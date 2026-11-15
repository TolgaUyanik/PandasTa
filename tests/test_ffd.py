# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.ffd` -- AFML's fixed-width window
fractional differencing of log price (issue #13). Every number quoted here
is printed by `docs/measure_ffd_proxy.py`; the full picture, including the
deferred Gate E, is in `docs/FfdMeasured.md`.

⚠ READ THIS FIRST. AFML's own `getWeights_FFD` recipe has two problems this
port does not ship unmodified (see `ffd.__doc__` for the full reasoning):

* The truncated weights do NOT sum to zero, and -- this is the part that
  bites, not just a ×8 nicety -- that non-zero sum makes the filtered value
  depend on where the caller's series happens to start. Measured directly,
  raw weights vs re-centred, at the IDENTICAL (d=0.4, threshold=1e-5):
  slicing a 4,000-bar walk at bar 100/500/900 and re-anchoring moves the
  value, vs the un-sliced run, by 1.3e-02 / 4.7e-02 / 6.3e-02 with the raw
  weights and 1.1e-15 / 1.3e-15 / 1.3e-15 with the weights `_ffd_weights`
  ships (`docs/measure_ffd_proxy.py`'s "Gate D defect" block runs both
  through the same experiment, so the pair is directly comparable).
  `_ffd_weights` re-centres by moving the sum onto the most-lagged kept
  weight, which fixes BOTH the anchor dependence and the scale test.
* AFML's own worked example picks `d` by ADF-testing the FULL sample -- a
  look-ahead the task flags. This port makes `d` a FIXED parameter instead;
  there is no estimation step in the module for a mutant to backdate, so
  Gate B instead pins the window-indexing arithmetic and the anchor choice.

What these tests pin, in order of how much it would hurt to lose:

* The RE-CENTRING ITSELF: sum(w) == 0 to float precision, over four (d,
  threshold) pairs. Every weight except the last is also cross-checked two
  ways against the closed-form generalised binomial coefficient
  `(-1)^k * C(d, k)`: a plain product loop (same formula, independent code
  path -- catches a sign/off-by-one bug in the module's recursion, not a
  conceptual mismatch with AFML's specific recipe, which this port could
  not check line-by-line against the printed book -- see
  `docs/FfdMeasured.md`), AND, for the first 40 weights where it cannot
  overflow, the Gamma function directly (`math.gamma`, a genuinely
  different numerical codepath from any product/recursion).
* CAUSALITY by future-perturbation, the same harness `kalman_trend` and
  other ports use: rewrite every bar from `j` onward, demand bars `[0:j]`
  bit-identical, over offsets past the warm-up. Two live mutants, each
  caught at every offset: the output write back-dated by one bar, and the
  anchor read from the END of the series instead of the start (a textbook
  look-ahead: it would make today's filtered value depend on next year's
  closing price).
* HEAD stability, not only the tail: starting the filter at bar s instead
  of bar 0 agrees with the full run from the first comparable bar on, to
  1e-9 at this module's actual defaults (measured worst 1.2e-15) -- the
  un-recentred version fails the same kind of check by seven orders of
  magnitude at (d=0.4, threshold=1e-5): see the bullet above.
* SCALE-FREE: bit-identical under x8 and x64 (measured 0.0, `Series.equals`
  True), within 1e-9 under x10 and x3.7 (measured 3.3e-16 / 4.4e-16) with
  matching NaN masks, and `0 < fires < n`.
* CORRECTNESS of the window arithmetic against an independently written
  convolution (plain Python loop, not `sliding_window_view`), including a
  NaN, a zero and a negative close.
* Bad input: non-finite/non-positive closes are skipped, not propagated;
  leading NaNs only shift the output; too few valid closes returns None;
  invalid `d` / `threshold` raise.
* Wiring: `Category`, the accessor, and the column name.
"""
import importlib
import types

import math

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.statistics.ffd import ffd, _ffd_weights

D, THRESH = 0.4, 1e-4
W = 282  # width at the defaults, printed by docs/measure_ffd_proxy.py


def _walk(n=4000, seed=11, sigma=0.02, tick=None):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return Series(c)


def _independent_binom_weight(d, k):
    """(-1)^k * C(d, k), via a plain product loop -- not the module's
    recursion. Same closed form as the module (so this catches a coding
    bug -- sign flip, off-by-one -- in the recursion, not a conceptual
    mismatch with AFML's specific published formula)."""
    c = 1.0
    for i in range(k):
        c *= (d - i) / (i + 1)
    return ((-1) ** k) * c


def _independent_gamma_weight(d, k):
    """(-1)^k * C(d, k) via math.gamma -- a genuinely different numerical
    codepath (no product loop, no recursion) from both the module and
    `_independent_binom_weight` above. Only safe for small k: Gamma of a
    large negative argument overflows well before AFML's own weights
    would underflow, which is why the recursion -- not Gamma directly --
    is how everyone computes this in practice."""
    if k == 0:
        return 1.0
    sign = -1.0 if k % 2 else 1.0
    c = math.gamma(d + 1) / (math.gamma(k + 1) * math.gamma(d - k + 1))
    return sign * c


def _naive_convolution(y, w):
    """FFD by a plain Python loop over explicit lags, as the Gate A oracle
    for the module's vectorised sliding-window-and-dot-product."""
    width = len(w)
    out = np.full(len(y), np.nan)
    for t in range(width - 1, len(y)):
        window = y[t - width + 1:t + 1]
        if np.isnan(window).any():
            continue
        out[t] = sum(w[k] * window[width - 1 - k] for k in range(width))
    return out


# ------------------------------------------------------------- re-centring


@pytest.mark.parametrize("d,threshold", [(0.4, 1e-5), (0.3, 1e-5), (0.5, 1e-5), (0.4, 1e-4)])
def test_weights_are_recentred_and_match_the_binomial_formula(d, threshold):
    w = _ffd_weights(d, threshold)
    assert abs(sum(w)) < 1e-9
    independent = [_independent_binom_weight(d, k) for k in range(len(w) - 1)]
    worst = max(abs(a - b) for a, b in zip(w[:-1], independent))
    assert worst < 1e-9


@pytest.mark.parametrize("d,threshold", [(0.4, 1e-5), (0.3, 1e-5), (0.5, 1e-5), (0.4, 1e-4)])
def test_weights_match_the_gamma_function_for_small_k(d, threshold):
    """A second oracle on a genuinely different numerical codepath (no
    product loop, no recursion) -- bounded to small k because Gamma of a
    large negative argument overflows well before these weights would."""
    w = _ffd_weights(d, threshold)
    k_max = min(40, len(w) - 1)
    worst = max(abs(w[k] - _independent_gamma_weight(d, k)) for k in range(k_max))
    assert worst < 1e-9


def _raw_afml_weights(d, threshold):
    """AFML Snippet 5.1 exactly as published, with no re-centring -- the
    oracle for how big the defect being corrected actually is."""
    w = [1.0]
    k = 1
    while True:
        wk = -w[-1] * (d - k + 1) / k
        if abs(wk) < threshold:
            break
        w.append(wk)
        k += 1
    return w


def test_the_uncorrected_sum_is_not_zero():
    """The defect the task flagged, measured directly: pin that it is real,
    not a strawman, so a future "simplification" cannot silently drop the
    re-centring step and still pass the scale tests above."""
    raw = _raw_afml_weights(D, THRESH)
    assert abs(sum(raw)) > 1e-3
    assert len(raw) == W  # re-centring only touches the last weight's value, not the count


# ------------------------------------------------------------ correctness


def test_width_at_the_defaults():
    assert len(_ffd_weights(D, THRESH)) == W


def test_matches_an_independent_convolution_including_bad_bars():
    close = _walk(2200)
    close.iloc[1500] = np.nan
    close.iloc[1700] = 0.0
    close.iloc[1900] = -5.0
    out = ffd(close, D, THRESH)
    vals = close.to_numpy(dtype=float)
    mask = np.isfinite(vals) & (vals > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        y = np.log(vals / vals[mask][0])
    y[~mask] = np.nan
    ref = _naive_convolution(y, _ffd_weights(D, THRESH))
    assert (np.isnan(out.values) == np.isnan(ref)).all()
    assert np.nanmax(np.abs(out.values - ref)) < 1e-9


# ------------------------------------------------------- head transient


def test_head_agrees_with_a_longer_run_from_the_first_comparable_bar():
    close = _walk(4000, seed=7)
    full = ffd(close, D, THRESH)
    worst = 0.0
    for s in (100, 500, 900):
        part = ffd(close.iloc[s:], D, THRESH)
        i = part.first_valid_index()
        assert i == s + W - 1
        worst = max(worst, (part.loc[i:] - full.loc[i:]).abs().max())
    assert worst < 1e-9


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    close = _walk(3000, seed=11, tick=0.05)
    assert ffd(close, D, THRESH).equals(ffd(close * k, D, THRESH))


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    close = _walk(3000, seed=11, tick=0.05)
    base, scaled = ffd(close, D, THRESH), ffd(close * k, D, THRESH)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    out = ffd(_walk(3000, seed=11, tick=0.05), D, THRESH).dropna()
    assert 0 < len(out) < 3000
    assert out.nunique() > 100


# --------------------------------------------------------------- bad input


@pytest.mark.parametrize("bad", [np.nan, 0.0, -1.0])
def test_a_bad_close_is_skipped_not_propagated(bad):
    close = _walk(3300)
    close.iloc[1600] = bad
    out = ffd(close, D, THRESH)
    assert np.isnan(out.iloc[1600:1600 + W]).all()  # every window covering bar 1600 is NaN
    assert np.isfinite(out.iloc[1600 + W:].values).all()


def test_leading_nans_only_shift_the_output():
    close = _walk(2500)
    padded = pd.concat([Series([np.nan] * 50), close], ignore_index=True)
    out = ffd(padded, D, THRESH)
    assert out.first_valid_index() == 50 + W - 1
    assert out.iloc[50:].reset_index(drop=True).equals(ffd(close, D, THRESH))


def test_too_few_valid_closes_returns_none():
    assert ffd(Series([np.nan] * 2000), D, THRESH) is None
    assert ffd(_walk(W), D, THRESH) is None


@pytest.mark.parametrize("kw", [{"d": 0}, {"d": 1}, {"d": -0.1}, {"d": 1.1}, {"d": np.nan},
                                {"threshold": 0}, {"threshold": -1e-5}, {"threshold": np.nan}])
def test_bad_parameters_raise(kw):
    with pytest.raises(ValueError, match="ffd"):
        ffd(_walk(2000), **kw)


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.statistics.ffd")


def _load_mutant(edits, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    for old, new in edits:
        assert src.count(old) == 1, f"mutation target {old!r} not unique"
        src = src.replace(old, new)
    mod = types.ModuleType(f"_ffd_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src, _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    "write_backdated": [("out[width - 1:] = win @ coef", "out[width - 2:-1] = win @ coef")],
    # the 🔴 failure class the task flagged: reading from the END of the
    # series as the anchor makes every bar depend on the series' last close.
    "future_anchor": [("anchor = usable[0]", "anchor = usable[-1]")],
}

OFFSETS = list(range(1600, 3800, 300))  # 8 offsets, all past the warm-up (W=282)


def _leaks(fn, width=W):
    close = _walk(4000)
    base = fn(close, D, THRESH)
    other = _walk(4000, seed=99)
    hits = 0
    for j in OFFSETS:
        pert = close.copy()
        pert.iloc[j:] = other.iloc[j:].values
        out = fn(pert, D, THRESH)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        if not a.equals(b):
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(ffd) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(MUTANTS[tag], tag)
    close = _walk(4000)
    assert not mod.ffd(close, D, THRESH).equals(ffd(close, D, THRESH))  # live
    assert _leaks(mod.ffd) == len(OFFSETS)                              # caught at every offset


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(2000)
    df = DataFrame({"open": close, "high": close, "low": close,
                    "close": close, "volume": 1.0})
    assert "ffd" in ta.Category["statistics"]
    out = df.ta.ffd()
    assert out.name == "FFD_0.4_0.0001"
    pd.testing.assert_series_equal(out, ffd(close))
    assert df.ta.ffd(d=0.3, threshold=1e-4).name == "FFD_0.3_0.0001"
