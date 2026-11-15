# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.g191_022` -- Guotai Junan's (2017,
"GTJA191") alpha `#22`, per issue #82:
`SMA((C-MEAN(C,6))/MEAN(C,6) - DELAY(that,3), 12, 1)`, matching the issue's
own prototype (`docs/issues/screen/ind_screen.py:317-321`). Gate A
derivation, including the one reading of the source string the string does
not fix on its own, is in the module docstring and
`docs/G191022Measured.md`. Gate E is MEASURED (issue-solver run
`is82-g191_022-19d9fa07`, 2026-11-11): `G191_022_6_3_12_1` max |rho| 0.8842
vs `smi_SMIo_5_20_5` (manifest, n = 397,158), per-frame max median 0.8861
over 89 frames -> DISCLOSE_GAP, under the 0.90 strike line, so the column
ships; row in `docs/gate_e_ledger.csv`. The module docstring still says
"Gate E is pending" and is deliberately NOT edited: the ledger row pins that
file's sha1 and the `pandas_ta` tree sha1 as measured, and touching either
would invalidate the recorded run.

What these tests pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every close bar from `j`
  onward (another synthetic walk), demand bars `[0:j]` bit-identical with
  matching NaN masks, over 37 offsets past the 19-bar warm-up. Three
  mutants (`importlib` source read, `exec`'d in memory), each shown live
  (differs from the real module) then caught at every one of the 37
  offsets: the final write index shifted `smooth_length=12` bars into the
  future; `rolling(bias_length, center=True)` in place of the causal
  trailing mean (the same `bos` look-ahead bug class CLAUDE.md documents);
  and `bias.shift(-delay_length)` in place of the backward `DELAY`, which
  is this formula's own most plausible sign slip.
* THE READING OF `DELAY(that,3)`. The source string's `that` back-reference
  is resolved as the BIAS (`bias[t] - bias[t-3]`), not as the whole
  subtraction. The rejected reading is not a cosmetic difference: measured
  on the 1,500-bar walk it is bit-equal on **0** bars, max |diff| 0.0214 on
  a column whose own range is [-0.0102, 0.0132], and Spearman 0.1312
  against the shipped column.
* CORRECTNESS: a hand-derived 8-bar example at `bias_length=2,
  delay_length=1, smooth_length=2`, every bar's arithmetic written out,
  including the `adjust=False` seeding of the GTJA recursion; plus a spot
  check at the shipped defaults against an independent per-bar computation
  (a plain Python loop over numpy scalars -- no `.rolling()`, no
  `.shift()`, no `.ewm()`), which agrees to **2e-17 absolute** rather than
  bit-for-bit, because pandas' rolling mean and `ewm` sum in a different
  order. And the retyped prototype expression, matched BIT-FOR-BIT on the
  1,500-bar frame; the run comparing against the REAL candidate loaded out
  of `docs/issues/screen/ind_screen.py` is `docs/measure_g191_022.py`'s,
  not this file's (the screen is gitignored, so a test may not depend on
  it).
* THE FORK'S `min_periods` ON THE GTJA `SMA`, disclosed as a convention
  rather than the source's: the prototype's own `sma` omits it, which
  moves the first fire from bar 19 to bar 8 (1,492 non-NaN instead of
  1,481) and changes NOTHING on the 1,481 bars both define -- bit-equal on
  all of them.
* THE SHIPPED `bias` IS THE SAME INNER TERM in the other spelling
  (`(close/SMA)-1`): equal to 1.11e-16 absolute, bit-equal on only 26 of
  1,495 bars, and the whole column rebuilt on top of it is Spearman 1.0
  with max |diff| 2.78e-17. The port spells the source's subtraction form
  because Gate A is settled bit-for-bit against the prototype.
* SCALE-FREE: bit-identical under price x8/x64 (power-of-two, exact in
  IEEE754), within float64 tolerance under x10/x3.7, NaN masks matching,
  plus `0 < fires < n` and 1,481 distinct values so a constant column
  cannot pass.
* NaN HANDLING, which is not what a reader would guess: one NaN in `close`
  empties no output bar at all (pandas `ewm` skips a NaN input and carries
  its previous value forward) while displacing 448 later bars' values.
  Measured, not assumed.
* THE `smooth_weight` GUARD'S OWN LIMIT, in all three bands, because the
  public docstring describes them: `m` is cast with `int()`, so
  `0 < m < 1` becomes `alpha = 0` and `m >= smooth_length + 1` gives
  `alpha > 1` (pandas' `ewm` raises on both — measured at 0.5, 13 and 20);
  but `smooth_length <= m < smooth_length + 1` becomes `alpha = 1.0`,
  which pandas ACCEPTS, leaving the column equal to the raw 3-bar change
  bit-for-bit with no error at all (measured at 12 and 12.5). The middle
  band is why the docstring does not promise an exception for "any
  `m > smooth_length`".
* Wiring: `Category`, the accessor, the column name `G191_022_6_3_12_1`,
  and the four tunables forwarded under their own names.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.momentum.bias import bias as shipped_bias
from pandas_ta.momentum.g191_022 import g191_022


def _walk(n=1500, seed=11, sigma=0.015):
    """Close-only lognormal walk -- the same frame `docs/measure_g191_022.py`
    measures on (`_walk`), so the counts in both agree by construction."""
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close, index=pd.RangeIndex(n))


# ------------------------------------------------------------ correctness


def test_hand_derived_eight_bars():
    """`bias_length=2, delay_length=1, smooth_length=2, smooth_weight=1`.

    close = [10, 11, 12, 11, 13, 14, 13, 15]
    mean2 = [nan, 10.5, 11.5, 11.5, 12, 13.5, 13.5, 14]
    bias  = (C - mean2)/mean2
          t1:  0.5/10.5   =  0.047619047619047616
          t2:  0.5/11.5   =  0.043478260869565216
          t3: -0.5/11.5   = -0.043478260869565216
          t4:  1.0/12     =  0.08333333333333333
          t5:  0.5/13.5   =  0.037037037037037035
          t6: -0.5/13.5   = -0.037037037037037035
          t7:  1.0/14     =  0.07142857142857142
    change = bias - DELAY(bias, 1)
          t2: -0.004140786749482402
          t3: -0.08695652173913043
          t4:  0.12681159420289855
          t5: -0.0462962962962963
          t6: -0.07407407407407407
          t7:  0.10846560846560846
    SMA(change, 2, 1) is `ewm(alpha=0.5, adjust=False, min_periods=2)`:
    the recursion is SEEDED with its first valid input (t2), which
    `min_periods=2` then masks, so the first value shown is t3:
          Y[t2] = -0.004140786749482402                     (masked)
          Y[t3] = 0.5*(-0.08695652173913043) + 0.5*Y[t2]
          Y[t4] = 0.5*( 0.12681159420289855) + 0.5*Y[t3]
          Y[t5] = 0.5*(-0.0462962962962963 ) + 0.5*Y[t4]
          Y[t6] = 0.5*(-0.07407407407407407) + 0.5*Y[t5]
          Y[t7] = 0.5*( 0.10846560846560846) + 0.5*Y[t6]
    """
    close = Series([10.0, 11.0, 12.0, 11.0, 13.0, 14.0, 13.0, 15.0])
    out = g191_022(close, bias_length=2, delay_length=1, smooth_length=2,
                   smooth_weight=1)

    b = [np.nan, 0.5 / 10.5, 0.5 / 11.5, -0.5 / 11.5, 1.0 / 12.0,
         0.5 / 13.5, -0.5 / 13.5, 1.0 / 14.0]
    change = [np.nan, np.nan] + [b[t] - b[t - 1] for t in range(2, 8)]
    y = change[2]
    expected = [np.nan, np.nan, np.nan]
    for t in range(3, 8):
        y = 0.5 * change[t] + 0.5 * y
        expected.append(y)

    assert out.iloc[:3].isna().all()
    for t in range(3, 8):
        assert out.iloc[t] == pytest.approx(expected[t], abs=1e-15), f"bar {t}"
    # the first shown value, written out as a number rather than a formula
    assert out.iloc[3] == pytest.approx(-0.045548654244306416, abs=1e-15)
    assert out.iloc[7] == pytest.approx(0.035006182424660685, abs=1e-15)


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 4 bars of the shipped defaults against an independent
    per-bar computation: a plain Python loop over numpy scalars, using
    neither `.rolling()` nor `.shift()` nor `.ewm()`. The GTJA recursion is
    seeded the way `adjust=False` seeds it (Y at the first valid input IS
    that input). The agreement is to float64 rounding, not bit-for-bit --
    pandas sums the rolling window and runs the recursion in a different
    order (measured: 2e-17 absolute at worst over the four bars)."""
    close = _walk(900, seed=5)
    out = g191_022(close)
    c = close.to_numpy(dtype=float)
    bias_length, delay_length, smooth_length = 6, 3, 12
    first_change = bias_length - 1 + delay_length

    def bias_at(i):
        mean = sum(c[i - bias_length + 1:i + 1]) / bias_length
        return (c[i] - mean) / mean

    def expected_at(t):
        alpha = 1.0 / smooth_length
        y = None
        for i in range(first_change, t + 1):
            ch = bias_at(i) - bias_at(i - delay_length)
            y = ch if y is None else alpha * ch + (1.0 - alpha) * y
        return y

    for t in (19, 300, 600, 899):
        assert out.iloc[t] == pytest.approx(expected_at(t), abs=2e-17), f"bar {t}"


def test_matches_the_prototype_expression_bit_for_bit():
    """The issue's own prototype (`docs/issues/screen/ind_screen.py:317-321`)
    is

        b = (c - mean(c, 6)) / mean(c, 6)
        return sma(b - delay(b, 3), 12, 1)

    with `mean(x, n) = x.rolling(n).mean()` (line 47),
    `delay(x, n) = x.shift(n)` (line 45) and `sma(x, n, m) =
    x.ewm(alpha=m/n, adjust=False).mean()` (lines 57-59). The port fixes one
    READING of the source string (see the module docstring) and adds this
    fork's `min_periods=n` to the GTJA `SMA`, but no arithmetic beyond the
    prototype, so on the bars both define it must agree EXACTLY, not within
    a tolerance: same bits.

    The expression below is RETYPED from those lines, because `docs/issues/`
    is gitignored and a clone running this suite does not have it.
    `docs/measure_g191_022.py` closes that gap where the file IS present: it
    loads `ind_screen.py` by path, calls the registered `g191_022` candidate
    itself, and prints both the port-vs-candidate and the
    retyped-vs-candidate comparisons -- on its 1,500-bar frame the port is
    bit-identical to the candidate on all 1,481 bars it defines, and the
    retyped expression is bit-identical to the candidate on all 1,492."""
    close = _walk()
    out = g191_022(close)

    mean6 = close.rolling(6).mean()
    b = (close - mean6) / mean6
    prototype = (b - b.shift(3)).ewm(alpha=1 / 12, adjust=False).mean()

    shared = out.notna() & prototype.notna()
    assert int(shared.sum()) == 1481
    assert (out[shared] == prototype[shared]).all()
    # ... and with the fork's own `min_periods`, the NaN masks match too.
    fork_spelled = (b - b.shift(3)).ewm(
        alpha=1 / 12, adjust=False, min_periods=12).mean()
    assert (out.isna() == fork_spelled.isna()).all()
    assert (out[out.notna()] == fork_spelled[out.notna()]).all()


def test_the_forks_min_periods_only_masks_bars_it_does_not_change_them():
    """`min_periods=n` on the GTJA `SMA` is this FORK's convention
    (`g191_109.py:101`, `g191_152.py:144`), not the source's: the
    prototype's own `sma` omits it (`ind_screen.py:57-59`). Measured on the
    1,500-bar walk, the difference is exactly 11 masked bars and nothing
    else: 1,481 non-NaN with it, 1,492 without, bit-equal on all 1,481."""
    close = _walk()
    out = g191_022(close)
    mean6 = close.rolling(6).mean()
    b = (close - mean6) / mean6
    source_spelled = (b - b.shift(3)).ewm(alpha=1 / 12, adjust=False).mean()

    assert int(out.notna().sum()) == 1481
    assert int(source_spelled.notna().sum()) == 1492
    assert int(source_spelled.notna().idxmax()) == 8   # first valid `change`
    assert int(out.notna().idxmax()) == 19             # + 11 masked bars
    shared = out.notna()
    assert (out[shared] == source_spelled[shared]).all()


def test_the_rejected_reading_of_the_back_reference_is_a_different_column():
    """`DELAY(that,3)`'s `that` is the BIAS, so the smoothed quantity is
    `bias[t] - bias[t-3]`. Reading `that` as the whole subtraction instead
    gives `bias - (bias - DELAY(bias,3)).shift(3)` -- a different column,
    not a cosmetic difference: measured on the 1,500-bar walk, bit-equal on
    0 bars, max |diff| 0.0214 (the shipped column's own range is
    [-0.0102, 0.0132]) and Spearman 0.1312."""
    close = _walk()
    out = g191_022(close)
    mean6 = close.rolling(6).mean()
    b = (close - mean6) / mean6
    rejected = (b - (b - b.shift(3)).shift(3)).ewm(
        alpha=1 / 12, adjust=False, min_periods=12).mean()

    shared = out.notna() & rejected.notna()
    assert int((out[shared] == rejected[shared]).sum()) == 0
    assert (out[shared] - rejected[shared]).abs().max() == pytest.approx(
        0.02137858239070601, rel=1e-9)
    rho = float(out[shared].corr(rejected[shared], method="spearman"))
    assert rho == pytest.approx(0.131234, abs=1e-6)


def test_the_inner_term_is_the_shipped_bias_to_float_tolerance():
    """`(C-MEAN(C,6))/MEAN(C,6)` is the same mathematical quantity as the
    shipped `bias(close, 6)`, which spells it `(close/SMA)-1`. The two are
    NOT bit-equal (measured locally: equal on 26 of 1,495 bars, max |diff|
    1.11e-16, max |rel diff| 3.50e-11; the CI runner's numpy measured 19, so
    the exact count is platform float detail and only "not all" is pinned),
    which is why the port spells the
    source's subtraction form -- Gate A is settled bit-for-bit against the
    prototype, and the prototype subtracts. Rebuilding the WHOLE column on
    top of the shipped `bias` instead moves it by at most 2.78e-17 and
    leaves Spearman 1.0, so the choice of spelling is a float detail, not a
    different indicator."""
    close = _walk()
    out = g191_022(close)
    mean6 = close.rolling(6).mean()
    own_term = (close - mean6) / mean6
    helper_term = shipped_bias(close, length=6)
    assert helper_term.name == "BIAS_SMA_6"

    m = own_term.notna() & helper_term.notna()
    assert int(m.sum()) == 1495
    assert (own_term[m] - helper_term[m]).abs().max() < 2e-16
    assert int((own_term[m] == helper_term[m]).sum()) < int(m.sum())  # not bit-equal

    via_helper = (helper_term - helper_term.shift(3)).ewm(
        alpha=1 / 12, adjust=False, min_periods=12).mean()
    vm = out.notna() & via_helper.notna()
    assert (out[vm] - via_helper[vm]).abs().max() < 1e-16
    assert float(out[vm].corr(via_helper[vm], method="spearman")) == pytest.approx(
        1.0, abs=1e-12)


def test_insufficient_history_returns_none():
    # defaults need bias_length + delay_length + smooth_length - 1 = 20 bars
    assert g191_022(_walk(19)) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    out = g191_022(_walk(20))
    assert out is not None
    assert out.iloc[:19].isna().all()
    assert pd.notna(out.iloc[19])


def test_default_name():
    assert g191_022(_walk()).name == "G191_022_6_3_12_1"


def test_distinct_parameters_produce_distinct_names_and_values():
    close = _walk(400)
    out1 = g191_022(close)
    out2 = g191_022(close, bias_length=10, delay_length=5, smooth_length=20,
                    smooth_weight=2)
    assert out1.name == "G191_022_6_3_12_1"
    assert out2.name == "G191_022_10_5_20_2"
    m = out1.notna() & out2.notna()
    assert (out1[m] != out2[m]).any()


@pytest.mark.parametrize("smooth_weight", [0.5, 13, 20])
def test_a_weight_that_leaves_alpha_outside_zero_one_raises(smooth_weight):
    """The Args docstring's first and third bands. `m` is cast with
    `int()`, so `smooth_weight=0.5` truncates to 0 (`alpha = 0`), while
    `13` and `20` against `smooth_length=12` give `alpha = 13/12` and
    `alpha = 5/3`; pandas' own `ewm` rejects all three. The boundary
    matters and is pinned by the test below, not here: `12 <= m < 13`
    truncates to `alpha = 1.0`, which pandas ACCEPTS. The guard is
    deliberately left sibling-consistent (`g191_152` validates the same
    way) rather than widened in this port."""
    with pytest.raises(ValueError, match="alpha"):
        g191_022(_walk(400), smooth_weight=smooth_weight)


@pytest.mark.parametrize("smooth_weight", [12, 12.5])
def test_a_weight_of_alpha_one_silently_disables_the_smoother(smooth_weight):
    """The band the docstring must NOT promise an exception for, and the
    reason the claim was narrowed: `m = 12` (and `m = 12.5`, which `int()`
    truncates to 12) against `smooth_length=12` gives `alpha = 1.0`, inside
    pandas' accepted `(0, 1]`. Nothing raises; the recursion keeps only its
    newest input, so the column becomes the raw 3-bar change of the bias on
    every firing bar — bit-for-bit — under a name that still says it is
    smoothed. Measured here rather than asserted."""
    close = _walk(400)
    out = g191_022(close, smooth_weight=smooth_weight)
    assert out is not None
    assert out.name == "G191_022_6_3_12_12"  # int() applied to both inputs

    mean6 = close.rolling(6).mean()
    bias = (close - mean6) / mean6
    change = bias - bias.shift(3)
    m = out.notna()
    assert int(m.sum()) == 381  # 400 - 19, the usual warm-up
    assert (out[m] == change[m]).all()  # no smoothing left at all


def test_a_single_nan_close_empties_no_output_bar_but_displaces_many():
    """Not what a reader would guess, so it is pinned: a NaN at bar 700
    empties `bias_length` bars of the mean and `bias_length + delay_length`
    bars of the change, but pandas' `ewm` SKIPS a NaN input (carrying its
    previous value forward) instead of emptying its output. Measured on the
    1,500-bar walk: no output bar changes NaN-ness, and the displacement
    starts at bar 700 and runs for hundreds of bars (448 locally, 647 on the
    CI runner: where it falls below float64 resolution is platform float
    detail, so only its start and a lower bound are pinned)."""
    close = _walk()
    out = g191_022(close)
    poked_close = close.copy()
    poked_close.iloc[700] = np.nan
    poked = g191_022(poked_close)

    assert (poked.isna() == out.isna()).all()          # nothing emptied
    moved = poked.index[(poked != out) & poked.notna() & out.notna()]
    assert len(moved) >= 400  # of the 1,481 bars that fire
    assert int(moved[0]) == 700 and int(moved[-1]) >= 1100
    assert (poked.iloc[:700] == out.iloc[:700])[out.iloc[:700].notna()].all()


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.momentum.g191_022")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_022_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


SHIPPED_MEAN = "mean6 = close.rolling(bias_length).mean()"
SHIPPED_CHANGE = "change = bias - bias.shift(delay_length)"
SHIPPED_RESULT = "result = _gtja_sma(change, smooth_length, smooth_weight)"

WRITE_SHIFT_MUTANT = (
    SHIPPED_RESULT,
    "result = _gtja_sma(change, smooth_length, smooth_weight).shift(-smooth_length)",
)
CENTERED_MEAN_MUTANT = (
    SHIPPED_MEAN,
    # the `bos` look-ahead bug class
    "mean6 = close.rolling(bias_length, center=True).mean()",
)
FORWARD_DELAY_MUTANT = (
    SHIPPED_CHANGE,
    # DELAY read forward: this formula's own most plausible sign slip
    "change = bias - bias.shift(-delay_length)",
)

OFFSETS = range(50, 1500, 40)  # past the 19-bar warm-up


def _leaks(fn):
    close = _walk(1500)
    other = _walk(1500, seed=97)
    base = fn(close)
    hits = 0
    for j in OFFSETS:
        poked = close.copy()
        poked.iloc[j:] = other.iloc[j:].values
        out = fn(poked)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(g191_022) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    close = _walk()
    assert not mod.g191_022(close).equals(g191_022(close))  # live
    assert _leaks(mod.g191_022) == len(list(OFFSETS))       # caught, every offset


def test_centered_mean_mutant_is_caught():
    mod = _load_mutant(*CENTERED_MEAN_MUTANT)
    close = _walk()
    assert not mod.g191_022(close).equals(g191_022(close))  # live
    assert _leaks(mod.g191_022) == len(list(OFFSETS))       # caught, every offset


def test_forward_delay_mutant_is_caught():
    mod = _load_mutant(*FORWARD_DELAY_MUTANT)
    close = _walk()
    assert not mod.g191_022(close).equals(g191_022(close))  # live
    assert _leaks(mod.g191_022) == len(list(OFFSETS))       # caught, every offset


# ------------------------------------------------------------ reachability


def test_fires_on_a_non_trivial_fraction():
    out = g191_022(_walk())  # 1500 bars, defaults
    assert int(out.notna().sum()) == 1481   # exactly n - 19, measured
    assert int(out.notna().idxmax()) == 19  # first fire at the warm-up bound


def test_fires_and_is_not_constant():
    out = g191_022(_walk())
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert int(out.dropna().nunique()) == 1481  # every firing bar distinct


def test_the_column_takes_both_signs_and_stays_near_zero():
    """A smoothed first difference of a small ratio: on the 1,500-bar walk
    749 bars are positive, 732 negative, none exactly zero, and the whole
    range is [-0.0102, 0.0132] with median 6.98e-05."""
    out = g191_022(_walk()).dropna()
    assert int((out > 0).sum()) == 749
    assert int((out < 0).sum()) == 732
    assert int((out == 0).sum()) == 0
    assert float(out.min()) == pytest.approx(-0.01020038, abs=1e-8)
    assert float(out.max()) == pytest.approx(0.01319801, abs=1e-8)
    assert float(out.median()) == pytest.approx(6.976e-05, abs=1e-8)


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    close = _walk()
    base = g191_022(close)
    scaled = g191_022(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    """The bound is the MEASURED worst case with one decade of headroom, not
    a round number: `docs/measure_g191_022.py` prints max |diff| 8.33e-17 at
    x10 and 5.81e-17 at x3.7, so the assertion is 1e-15. A looser 1e-12
    would let a 10,000x degradation of scale-invariance pass the test that
    exists to catch it."""
    close = _walk()
    base = g191_022(close)
    scaled = g191_022(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-15


def test_price_scale_leaves_the_sign_of_every_bar_alone():
    """The column is signed, so a rescale that preserved magnitudes but
    flipped a near-zero bar's sign would still break the feature. Measured
    at all four multipliers on the 1,500-bar walk: no bar changes sign."""
    close = _walk()
    base = g191_022(close)
    m = base.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_022(close * k)
        assert (np.sign(base[m]) == np.sign(scaled[m])).all(), f"k={k}"


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(400)
    df = pd.DataFrame({"open": close, "high": close, "low": close,
                       "close": close})
    assert "g191_022" in ta.Category["momentum"]
    out = df.ta.g191_022()
    assert out.name == "G191_022_6_3_12_1"
    pd.testing.assert_series_equal(out, g191_022(close))
    # every tunable forwarded under its own name -- the "supertrend failure
    # mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.g191_022(bias_length=10, delay_length=5, smooth_length=20,
                             smooth_weight=2)
    assert renamed.name == "G191_022_10_5_20_2"
    pd.testing.assert_series_equal(
        renamed,
        g191_022(close, bias_length=10, delay_length=5, smooth_length=20,
                 smooth_weight=2),
    )
