# -*- coding: utf-8 -*-
"""`wilder_rma` — true Wilder smoothing, shipped ALONGSIDE `rma`.

Pinned here, in order of how much it would hurt to lose:

1. **`rma`, `atr` and `natr` are byte-identical to what they were.** This is the
   whole reason the correction ships as a new callable instead of a fix in
   place. `natr` feeds a live paper-trading threshold (`ML_Position: natr >
   3.11`) under the 2026-07-27 trading freeze, and mined strategy rules in the
   parent repo match on exact column values. If `test_the_incumbents_did_not_move`
   ever fails, something changed that moves live thresholds — do not "fix" the
   expected values.
2. **Gate A: `wilder_rma` reproduces Pine v6 `ta.rma` exactly** — measured
   max |diff| **0.000e+00** over 287 settled bars at `length=14`. The reference
   is written out longhand in this file, deliberately not by calling the
   subject.
3. **The size of the defect that motivated this**, so nobody "simplifies"
   `wilder_rma` back into `rma`: on a 300-bar walk at `length=14` the two
   disagree on **285 of 287 settled bars**, max |diff| **0.241**. Seeding is
   not the only difference — Pine also differs from a bare
   `ewm(alpha, adjust=False)` by up to **0.636**, because that form has no SMA
   seed. A "fix" that only flips `adjust` is still wrong.
4. **All four call surfaces reach it**: module, `df.ta` accessor, `Category`
   (so `df.ta.strategy()` sweeps it), and the `ma()` dispatcher as `"wrma"` —
   which is what makes `atr(mamode="wrma")` produce `ATRwr_14` -- two
   letters, because `atr` names itself from `mamode[0]` and "wma" already
   owns `ATRw_14`. Touch point 3
   and 4 have drifted apart in this package before; that is what
   `tests/test_wiring_accessors.py` exists for and this is the local pin.
5. **Gate B: causality.** Value at bar T reads only bars <= T, proven with a
   mutant that READS THE FUTURE: the real module is shown clean and the mutant
   is shown caught. Note what this does and does not cover — a mutant that
   merely shifts the write index is *not* caught, because a consistent lag
   still reproduces on every prefix. That was tried and is recorded in the test
   body so nobody re-adds it believing it proves something.

NOT claimed: `wilder_rma` is not scale-free. It is a price-level (`PX`) column
exactly as `rma`, `sma` and `ema` are, and like them it needs a relational
companion before it is an ML feature. Gate D does not apply to it any more than
it applies to `rma`; see `docs/MLCompanionContract.md`.
"""
import numpy as np
import pytest
from pandas import DataFrame, Series

import pandas_ta as ta

LENGTH = 14


def frame(n=300, seed=11):
    rng = np.random.default_rng(seed)
    close = Series(100 * np.exp(np.cumsum(rng.normal(0, 0.011, n))),
                   name="close")
    return DataFrame({
        "open": close, "high": close * 1.01,
        "low": close * 0.99, "close": close,
    })


def pine_rma(src, length):
    """Pine v6 `ta.rma`, written longhand.

    `rma = na(rma[1]) ? ta.sma(src, length) : alpha * src + (1-alpha) * rma[1]`

    Deliberately a slow explicit loop that does NOT call the subject: a
    reference implemented by calling the thing it certifies proves nothing, a
    trap this repo has already fallen into once.
    """
    alpha = 1.0 / length
    out = Series(np.nan, index=src.index, dtype="float64")
    seed = src.rolling(length).mean()
    prev = np.nan
    for i in range(len(src)):
        if np.isnan(prev):
            if not np.isnan(seed.iloc[i]):
                prev = seed.iloc[i]
        else:
            prev = alpha * src.iloc[i] + (1 - alpha) * prev
        out.iloc[i] = prev
    return out


# --------------------------------------------------------------- 1. incumbents

def test_the_incumbents_did_not_move():
    """`rma`, `atr`, `natr` unchanged. Read the module docstring before editing."""
    df = frame()
    close, high, low = df["close"], df["high"], df["low"]

    old_rma = close.ewm(alpha=1.0 / LENGTH, min_periods=LENGTH).mean()
    assert (ta.rma(close, length=LENGTH) - old_rma).abs().max() == 0.0
    assert ta.rma(close, length=LENGTH).name == f"RMA_{LENGTH}"

    # Deliberately NOT `ta.ma("rma", tr, ...)`: that is the branch `atr`
    # itself calls, so repointing the dispatcher at `wilder_rma` -- the single
    # most likely future "simplification", and this task just edited that
    # dispatcher -- would move `atr` and its expected value together and this
    # test would stay green. Compare against the formula instead.
    tr = ta.true_range(high, low, close)
    expected_atr = tr.ewm(alpha=1.0 / LENGTH, min_periods=LENGTH).mean()
    atr_default = ta.atr(high, low, close, length=LENGTH)
    assert (atr_default - expected_atr).abs().max() == 0.0
    assert atr_default.name == f"ATRr_{LENGTH}"

    # `natr` carries the one live threshold in the repo (ML_Position:
    # natr > 3.11), so it gets a value assertion AND frozen golden constants.
    # A golden literal cannot be moved by an implementation change.
    #
    # ⚠ `natr` defaults to `mamode="ema"` (natr.py:10), NOT "rma" -- so it does
    # NOT inherit the `rma` defect at all. The live-threshold exposure is via
    # `atr`, whose default IS "rma". Worth stating precisely: an earlier
    # version of this file implied natr routed through rma, and asserted it
    # against `100 * <rma-smoothed atr> / close`, which is off by up to 0.149.
    natr = ta.natr(high, low, close, length=LENGTH)
    assert natr.name == f"NATR_{LENGTH}"
    ema_atr = ta.atr(high, low, close, length=LENGTH, mamode="ema")
    assert (natr - (100 * ema_atr / close)).abs().max() < 1e-15
    golden = [2.180799154194836, 2.164590623923742, 2.133112875957642,
              2.098673258704286, 2.089573427600442]
    assert [float(v) for v in natr.dropna().iloc[:5]] == golden, (
        f"natr moved: {[float(v) for v in natr.dropna().iloc[:5]]}"
    )

    assert (ta.ma("rma", close, length=LENGTH)
            - ta.rma(close, length=LENGTH)).abs().max() == 0.0


# ------------------------------------------------------------------- 2. Gate A

def test_gate_a_matches_pine_exactly():
    close = frame()["close"]
    mine = ta.wilder_rma(close, length=LENGTH)
    reference = pine_rma(close, LENGTH)
    both = ~(mine.isna() | reference.isna())
    assert both.sum() == 287, f"expected 287 settled bars, got {both.sum()}"
    assert (mine[both] - reference[both]).abs().max() == 0.0


@pytest.mark.parametrize("length", [2, 5, 14, 30, 50])
def test_gate_a_holds_across_lengths(length):
    close = frame()["close"]
    mine = ta.wilder_rma(close, length=length)
    reference = pine_rma(close, length)
    both = ~(mine.isna() | reference.isna())
    assert both.sum() > 0
    assert (mine[both] - reference[both]).abs().max() < 1e-12


# ------------------------------------------------------- 3. the defect's size

def test_it_is_measurably_different_from_rma():
    """If this ever passes trivially, `rma` was silently changed."""
    close = frame()["close"]
    mine = ta.wilder_rma(close, length=LENGTH)
    incumbent = ta.rma(close, length=LENGTH)
    both = ~(mine.isna() | incumbent.isna())
    differing = (mine[both] - incumbent[both]).abs() > 1e-9
    assert differing.sum() == 285, (
        f"expected 285 differing bars, got {differing.sum()} -- if this moved, "
        f"one of the two implementations changed"
    )
    assert (mine[both] - incumbent[both]).abs().max() == pytest.approx(
        0.241, abs=0.001)


def test_flipping_adjust_alone_would_not_have_fixed_it():
    """The seed matters too, so a one-character 'fix' is still wrong."""
    close = frame()["close"]
    naive = close.ewm(alpha=1.0 / LENGTH, min_periods=LENGTH,
                      adjust=False).mean()
    reference = pine_rma(close, LENGTH)
    both = ~(naive.isna() | reference.isna())
    assert (naive[both] - reference[both]).abs().max() == pytest.approx(
        0.636, abs=0.001)


# ---------------------------------------------------------------- 4. surfaces

def test_every_call_surface_reaches_it():
    df = frame()
    expected = f"WRMA_{LENGTH}"
    assert ta.wilder_rma(df["close"], length=LENGTH).name == expected
    assert df.ta.wilder_rma(length=LENGTH).name == expected
    assert ta.ma("wrma", df["close"], length=LENGTH).name == expected
    assert "wilder_rma" in ta.Category["overlap"]
    assert "wrma" in ta.ma()


def test_atr_can_use_it_without_changing_its_default():
    df = frame()
    high, low, close = df["high"], df["low"], df["close"]
    default = ta.atr(high, low, close, length=LENGTH)
    wilder = ta.atr(high, low, close, length=LENGTH, mamode="wrma")
    assert default.name == f"ATRr_{LENGTH}"
    assert wilder.name == f"ATRwr_{LENGTH}", (
        "the column name must encode which smoothing was used -- naming is API "
        "in this package and mined rules match on these strings"
    )
    # The reason it is `wr` and not `w`: `atr` named itself from `mamode[0]`,
    # so "wma" and "wrma" BOTH produced ATRw_14 -- two different indicators,
    # one column name, second write silently overwriting the first. The
    # assertion above used to read ATRw_14 and passed while the property its
    # own message claimed was false.
    assert ta.atr(high, low, close, length=LENGTH, mamode="wma").name         == f"ATRw_{LENGTH}", "pre-existing mamode names must not move"
    assert ta.atr(high, low, close, length=LENGTH, mamode="wma").name         != wilder.name, "the collision is back"
    both = ~(default.isna() | wilder.isna())
    assert (default[both] - wilder[both]).abs().gt(1e-9).sum() == 218


# ------------------------------------------------------------------- 5. Gate B

@pytest.mark.parametrize("cut", [50, 120, 200, 280])
def test_gate_b_causality_with_a_mutant(cut):
    """Real module clean; a back-dated mutant caught.

    Truncating a prefix cannot detect back-dating -- a module that writes bar
    T-1 from bar T still agrees with itself on every prefix. So the mutant is
    built by rewriting the write index in the module source and exec'ing it.
    """
    import importlib.util

    close = frame()["close"]

    # the real thing: recomputing on a prefix must reproduce the prefix
    full = ta.wilder_rma(close, length=LENGTH)
    prefix = ta.wilder_rma(close.iloc[:cut], length=LENGTH)
    both = ~(full.iloc[:cut].isna() | prefix.isna())
    assert both.sum() == cut - (LENGTH - 1), (
        f"expected {cut - (LENGTH - 1)} comparable bars at cut={cut}"
    )
    assert (full.iloc[:cut][both] - prefix[both]).abs().max() < 1e-12

    # The mutant must read the FUTURE, not merely be misaligned. Shifting the
    # write index instead (`wrma.iloc[length - 2:-1] = ...`) was tried first and
    # is NOT caught here -- and correctly so: it lags the whole output
    # consistently, so every prefix still reproduces. That is a lag defect, and
    # a prefix test is genuinely blind to it. Look-ahead is what this test
    # certifies, so the mutation makes each bar read the bar after it.
    spec = importlib.util.find_spec("pandas_ta.overlap.wilder_rma")
    source = open(spec.origin, encoding="utf8").read()
    mutated = source.replace(
        "tail = usable.iloc[length - 1:].copy()",
        "tail = usable.shift(-1).iloc[length - 1:].copy()")
    assert mutated != source, "the mutation did not apply -- the test is blind"

    namespace = {}
    exec(compile(mutated, "<mutant>", "exec"), namespace)
    mutant_full = namespace["wilder_rma"](close, length=LENGTH)
    mutant_prefix = namespace["wilder_rma"](close.iloc[:cut], length=LENGTH)
    both = ~(mutant_full.iloc[:cut].isna() | mutant_prefix.isna())
    delta = (mutant_full.iloc[:cut][both] - mutant_prefix[both]).abs()
    assert delta.max() > 1e-9, (
        f"the mutant was NOT caught at cut={cut}, so this cannot certify "
        f"causality"
    )
    # Say WHERE it is caught, so the test documents its own mechanism: a
    # look-ahead of horizon k is visible only in the last k bars of a cut.
    assert delta[delta > 1e-9].index.tolist() == [close.index[cut - 1]], (
        "expected the boundary bar alone to differ"
    )


# ------------------------------------------------------------------ behaviour

def test_it_returns_none_below_its_window():
    assert ta.wilder_rma(Series([1.0, 2.0, 3.0]), length=14) is None


def test_warmup_is_exactly_length_minus_one():
    close = frame()["close"]
    out = ta.wilder_rma(close, length=LENGTH)
    assert out.isna().sum() == LENGTH - 1
    assert out.notna().iloc[LENGTH - 1]


# ----------------------------------------------------------------- NaN paths

def test_leading_nans_are_warmup_and_are_skipped():
    """`true_range` has no value at bar 0, so this path is load-bearing:
    without it `atr(mamode="wrma")` returns None outright."""
    df = frame()
    tr = ta.true_range(df["high"], df["low"], df["close"])
    assert np.isnan(tr.iloc[0]), "fixture assumption: tr starts NaN"
    out = ta.wilder_rma(tr, length=LENGTH)
    assert out is not None
    assert out.notna().sum() > 0
    # first value lands one bar later than on a clean series, not never
    assert out.first_valid_index() == LENGTH


def test_a_nan_in_the_first_window_slides_the_seed_and_matches_pine():
    """It must not annihilate the series, and it must agree with the reference.

    An earlier version refused outright when the first window was dirty --
    throwing away 281 of 300 bars over one missing value -- while `pine_rma`
    returned all 281. Averaging a short seed would be wrong; refusing the
    column is not the only alternative to that.
    """
    close = frame()["close"].copy()
    close.iloc[5] = np.nan

    out = ta.wilder_rma(close, length=LENGTH)
    assert out is not None
    assert out.notna().sum() == 281

    reference = pine_rma(close, LENGTH)
    both = ~(out.isna() | reference.isna())
    assert both.sum() == 281
    assert (out[both] - reference[both]).abs().max() < 1e-12, (
        "sliding the seed must land on the same window Pine lands on"
    )


def test_it_returns_none_only_when_no_clean_window_exists_anywhere():
    from pandas import Series as S
    assert ta.wilder_rma(S([np.nan] * 50), length=LENGTH) is None
    # 10 real bars is fewer than `length`, so no full clean window exists
    assert ta.wilder_rma(S([np.nan] * 290 + [1.0] * 10), length=LENGTH) is None
    # ... but 14 real bars at the very end IS a clean window
    assert ta.wilder_rma(S([np.nan] * 286 + [1.0] * 14),
                         length=LENGTH) is not None


def test_a_duplicate_index_does_not_raise():
    """`index.get_loc` returns a MASK on a duplicate index and `.iloc` then
    raises. Plain `rma` survives that input, so refusing it would be a
    regression against the neighbour this ships beside."""
    close = frame()["close"].copy()
    close.index = [0] * close.size
    assert ta.rma(close, length=LENGTH) is not None, "fixture assumption"
    out = ta.wilder_rma(close, length=LENGTH)
    assert out is not None
    assert out.notna().sum() == close.size - (LENGTH - 1)


def test_trailing_nans_emit_the_carried_value_not_nan():
    """Stated in the docstring; pinned here because it is a fabricated
    observation, not a gap, and a reader must not be surprised by it."""
    close = frame()["close"].copy()
    close.iloc[-5:] = np.nan
    out = ta.wilder_rma(close, length=LENGTH)
    tail = out.iloc[-5:]
    assert tail.notna().all(), "the carry emits values on bars with no data"
    assert tail.nunique() == 1, "and they are all the same carried value"


def test_a_nan_after_the_seed_is_skipped_and_diverges_from_the_naive_recursion():
    """The documented divergence, measured -- not a claim.

    Skipping is the deliberate choice: real BIST frames have gaps and
    poisoning the remainder of a series over one missing bar makes the column
    useless. Gate A equality with Pine is therefore claimed on NaN-free input.
    """
    close = frame()["close"].copy()
    close.iloc[20] = np.nan

    out = ta.wilder_rma(close, length=LENGTH)
    assert out is not None
    assert out.isna().sum() == LENGTH - 1, (
        "only the warm-up should be NaN -- the gap is carried across, not "
        "propagated"
    )

    naive = pine_rma(close, LENGTH)
    assert naive.isna().sum() > LENGTH - 1, (
        "the naive recursion is expected to poison everything after the gap"
    )
    both = ~(out.isna() | naive.isna())
    assert both.sum() > 0
    assert (out[both] - naive[both]).abs().max() == pytest.approx(
        1.397, abs=0.01), "the documented 1.397 divergence moved"
