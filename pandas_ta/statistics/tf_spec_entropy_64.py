# -*- coding: utf-8 -*-
"""Spectral Entropy of Daily Returns (TFSPECENT) -- port of TSFEL's
`spectral_entropy` (BSD-3-Clause), https://github.com/fraunhoferportugal/tsfel,
`tsfel/feature_extraction/features.py`, as PandasTa issue #111 states it:

    features.py spectral_entropy: normalised entropy of the power spectrum

⚠ That one line, quoted from the issue, is the WHOLE of the source text
available here. TSFEL is not installed in this worktree, `docs/pine/` does not
carry it, and web access is unavailable, so Gate A does NOT read TSFEL's own
code: `tests/test_tf_spec_entropy_64.py::test_the_source_library_is_not_readable_here`
asserts that, so the limitation fails loudly if the environment ever changes.
What Gate A checks is the QUANTITY that line names -- the Shannon entropy of
the normalised power spectrum, divided by the entropy of the flat spectrum --
spelled three independent ways (a scalar-loop DFT built from `cmath`, numpy's
complex `fft` rather than `rfft`, and the screen prototype) and compared against
this module. Three oracles, and that count is the same in
`docs/TfSpecEntropy64Measured.md` §A and in the test module: §A4's DC-keeping
variant is NOT a fourth, it is the reading this port did not take. Nothing here
is evidence about how TSFEL handles an edge the issue does not name.

The scale-free form is the owner's screen prototype,
`docs/issues/screen/ind_screen_r2.py:229-252` (candidate `tf_spec_entropy_64`,
local to the owner's machine -- `docs/issues/` is gitignored):

    def _spec(W):
        F = np.abs(np.fft.rfft(W - W.mean(1, keepdims=True), axis=1))[:, 1:]
        f = np.fft.rfftfreq(W.shape[1])[1:]
        return f, F

    def f(W):
        _, F = _spec(W)
        P = F ** 2
        p = P / np.where((s := P.sum(1, keepdims=True)) == 0, np.nan, s)
        return -np.where(p > 0, p * np.log2(np.where(p > 0, p, 1)), 0).sum(1) \
               / np.log2(P.shape[1])
    roll(ret(c), 64, f)

CALCULATION.  Over the `length` simple returns ending at, and including, the
current bar: subtract the window's mean, take `np.fft.rfft`, drop bin 0 (the
DC bin), square the magnitudes into a power spectrum `P`, normalise it to
`p = P / sum(P)`, and return `-sum(p * log2(p)) / log2(len(p))`. `len(p)` is
`length // 2` -- 32 at the default `length` 64 -- so the divisor is the entropy
of a perfectly flat spectrum and the column is bounded in `[0, 1]`.

⚠ The mean is subtracted AND bin 0 is dropped, which is one removal too many on
paper and not in floating point: centring leaves bin 0 at the rounding residue
of a cancelling sum rather than at exactly zero, and it perturbs the other bins
in their last bits. Both steps are the prototype's and both are kept, because
the prototype is the expression the 2026-10-24 screen measured. Dropping the
centring moves the column by at most 5.254e-16 relative over seven 1,500-bar
frames (§A7 of `docs/TfSpecEntropy64Measured.md`). Keeping bin 0 instead, and
normalising by the number of non-zero probabilities the way a literal reading
of the source line would, is a DIFFERENT column: up to 0.0088 apart, Spearman
0.9865 .. 1.0000 over the same frames (§A4).

TWO DIVERGENCES from the prototype, both at the undefined windows, both in the
direction this fork's contract requires (`tf_centroid_20`, `maxvol_adv`,
`entropy`: never emit a magic number for an undefined ratio):

1. A window whose centred power is identically zero -- `length` equal returns,
   which a flat price and an exact geometric ramp both produce -- is NaN here.
   The prototype's `np.where(s == 0, np.nan, s)` looks like the same guard and
   is not: the NaN it injects is swallowed by the `p > 0` mask two lines later
   and the window comes out as **-0.0**, a legible entropy reading for a window
   that has no spectrum at all.
2. A window holding a non-finite return is NaN here, and **-0.0** in the
   prototype, by the same mechanism. Every frame has at least one such window,
   because `pct_change` makes bar 0 NaN: at the default `length` that is
   exactly bar 63, the bar before the first reading.

Measured over nine synthetic frames -- eight of 1,500 bars, and the exact x2
`ramp` of 200, whose step has to be a power of two over a short frame or its
returns are equal only to the last bits (§A1): 10,052 bars are defined by both
and 0 of them differ by a bit, while the prototype reads -0.0 on 1,581 bars
where this module reads NaN -- one per frame on the seven with a spectrum, all
1,437 of the flat frame and all 137 of the ramp. The bit-equality holds at
`length` 4, 5, 8, 20, 64 and 250 (§A1).

CAUSALITY.  The window is a plain trailing `sliding_window_view` ending at bar
`T`; nothing is shifted forward. `tests/test_tf_spec_entropy_64.py` proves this
by future-perturbation sweeps and by five mutants read off this file, edited
and exec'd in memory.

SCALE-FREE.  The input is `close.pct_change(fill_method=None)`, a ratio, so a
uniform price rescale cancels before the transform: bit-identical under an
exact binary factor (x8, x64, and measured out to 2**-40, 2**40 and 2**100, on
seven frames, and under x8 at `length` 4 / 5 / 8 / 20 / 64 / 250), and within
3.090e-14 relative under an arbitrary one (x10, x3.7, x0.1, x1.0000001). A
level SHIFT is not a rescale and does move the column: +1 on a level-100 walk
moves all 1,436 fired bars, by up to 1.989e-04. Measured in the test file and
in `docs/measure_tf_spec_entropy_64.py`, not assumed.
"""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: Fewest returns a window may hold. `np.fft.rfft` of a `length`-point window
#: returns `length // 2 + 1` bins, and dropping the DC bin leaves `length // 2`
#: of them, which is what the normaliser `log2(length // 2)` counts. At
#: `length` 2 and 3 that is `log2(1) = 0` and every window would be 0/0, so a
#: smaller or missing `length` falls back to the default rather than producing
#: a column of NaN.
MIN_LENGTH = 4
#: Doubles of WINDOW to transform at once. The transform has to materialise a
#: `(rows, length)` copy -- the spectrum reads the whole window, so there is
#: nothing a window can inherit from its neighbour -- and this budget is what
#: keeps the peak off the product `len(close) * length`: the rows per chunk are
#: `CHUNK_VALUES // length`. Measured on 400,000 bars (§Z), traced peak with
#: the budget against the same run with the budget raised out of reach:
#: 58.1 MB vs 636.8 MB at `length` 64, and 57.9 MB vs 2,458.1 MB at `length`
#: 250. It cannot change a value, because every
#: chunk is an independent run of rows:
#: `tests/test_tf_spec_entropy_64.py::test_the_chunk_budget_cannot_change_a_value`
#: runs the default against budgets of 1, 64, 999 and 10**9.
CHUNK_VALUES = 1 << 21


def _spectral_entropy(win, norm):
    """Normalised spectral entropy of each row of `win`, oldest value first.

    `win` is a `(rows, length)` block of returns. NaN rows and rows whose
    centred power is identically zero come back as NaN; everything else is the
    quantity the module docstring states.
    """
    centred = win - win.mean(axis=1, keepdims=True)
    # [:, 1:] drops the DC bin. See the module docstring on why the centring
    # above is kept even though this line makes it redundant in exact
    # arithmetic.
    power = np.abs(np.fft.rfft(centred, axis=1))[:, 1:] ** 2
    total = power.sum(axis=1)
    # `total` is 0 only for a window of `length` EQUAL returns and NaN only for
    # one holding a non-finite return; both are masked out below, so the
    # substituted 1.0 never reaches a shipped value. It is here so the division
    # cannot raise or warn, not to stand in for anything.
    p = power / np.where(total > 0.0, total, 1.0)[:, None]
    # log2(0) is -inf and 0 * -inf is NaN, so the zero bins are dropped from
    # the sum instead of being evaluated. A bin is exactly 0 when the window is
    # exactly periodic at another bin's frequency.
    positive = p > 0.0
    entropy = -np.where(positive, p * np.log2(np.where(positive, p, 1.0)),
                        0.0).sum(axis=1) / norm
    # A window is a reading only when every return in it is finite and its
    # centred power is not identically zero. Both of the excluded cases reach
    # `entropy` as -0.0 rather than as NaN, which is the prototype's behaviour
    # and the one thing this port deliberately does not copy.
    ok = np.isfinite(win).all(axis=1) & (total > 0.0)
    return np.where(ok, entropy, np.nan)


def tf_spec_entropy_64(close, length=None, offset=None, **kwargs):
    """Indicator: Spectral Entropy of Daily Returns (TFSPECENT)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 64
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
        norm = np.log2(length // 2)
        step = max(1, CHUNK_VALUES // length)
        for a in range(0, rows, step):
            b = min(a + step, rows)
            out[length - 1 + a:length - 1 + b] = \
                _spectral_entropy(win[a:b], norm)

    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    result.name = f"TFSPECENT_{length}"
    result.category = "statistics"

    return result


tf_spec_entropy_64.__doc__ = \
"""Spectral Entropy of Daily Returns (TFSPECENT)

How evenly the last `length` daily returns spread their power over
frequency, 0..1: 1 is a flat (white) spectrum, 0 is one dominant cycle.

Source: TSFEL (Fraunhofer Portugal AICOS, BSD-3-Clause),
https://github.com/fraunhoferportugal/tsfel,
`tsfel/feature_extraction/features.py` `spectral_entropy`, which PandasTa
issue #111 quotes as "normalised entropy of the power spectrum". ⚠ That
quote is the entire source text available in this worktree: TSFEL is not
installed, and web access is unavailable, so Gate A checks the quantity
the line names -- spelled as a scalar-loop DFT, as numpy's complex `fft`,
and as the owner's screen prototype -- and NOT TSFEL's own code. See
`docs/TfSpecEntropy64Measured.md` §A.

The scale-free form (DC removed) is the owner's screen prototype,
`docs/issues/screen/ind_screen_r2.py`, candidate `tf_spec_entropy_64`.
This module is bit-identical to it on every bar both define, and
deliberately differs on the two kinds of window the prototype reads as
-0.0: one holding a non-finite return, and one whose `length` returns are
all EQUAL (a flat price, a perfect geometric ramp). Those are NaN here --
a window with no spectrum is missing data, not an entropy of zero.

**What moves it.** Measured on 1,500-bar synthetic frames
(`python docs/measure_tf_spec_entropy_64.py L`): a Gaussian random walk
reads a mean of 0.8837 (sd 0.0260), a heavy-tailed (Student-t, df 2) walk
0.8958, and a frame whose returns carry one sinusoid on bin 8 plus light
noise 0.1364. A sinusoid alone, exactly on a bin, reads 1.3e-27 .. 3.3e-25
over bins 1, 2, 8 and 16 -- near zero but never exactly zero -- which is
section **A5**, not L; and the SAME sinusoid off the bin grid reads a mean
of 0.4303 at bin 8.5 and 0.2429 at bin 8.25 (§L2). That gap is
spectral leakage, not a different cycle, and it is the column's main
artefact: there is no window function, because TSFEL applies none and
neither does this port.

⚠ It is BLIND to the sign and the size of the returns, which is what makes
it not a volatility measure. Scaling the whole return window by -1, 0.5 or
2 leaves the value bit-identical; an inexact factor (-3.7, 1e6) moves it
by at most 5.184e-16 relative (measured on the arithmetic, §L3). What it
reads is the SHAPE of the return spectrum and nothing about its size.

⚠ It is also blind to WHERE in the window a pattern sits and to which
way round it runs, because `abs(rfft(.))` discards phase: rotating a
window circularly, or reversing it end to end, moves the value by at
most 4.441e-16 over 2,000 random windows (§L5). A general PERMUTATION is
not one of those symmetries and does move it -- by up to 0.135 on the
same windows -- so the column is not order-blind, only phase-blind.

Calculation:
    Default Inputs:
        length=64
    RET   = close / close[1] - 1
    W     = RET[T - length + 1 .. T] - mean(RET[T - length + 1 .. T])
    P     = abs(rfft(W))[1:] ** 2        # power, DC bin dropped
    p     = P / SUM(P)
    TFSPECENT = -SUM(p * log2(p)) / log2(length // 2)
    NaN while the window is incomplete, when it holds a non-finite
    return, and when SUM(P) is 0 (all `length` returns equal)

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window. At least 4 -- below that the
        normaliser log2(length // 2) is 0 -- so a smaller or missing
        value falls back to the default. Default: 64
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TFSPECENT_{length}, dimensionless, in [0, 1]
"""
