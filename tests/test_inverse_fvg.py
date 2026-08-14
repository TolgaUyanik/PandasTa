# tests/test_inverse_fvg.py
"""inverse_fvg (IFVG) -- a volatility-filtered Fair Value Gap that price
later closes back THROUGH flips polarity into an opposite-bias zone,
tracked until mitigation (TVPTA-6 candidate 14, ported from the IFVG half
of "Liquidity Sweeps & Inverse FVGs [LuxAlgo]"). Self-contained on
synthetic data.

Reachability tests `import pandas_ta` (`.context`), NOT `importlib.util.
spec_from_file_location` (see TODO.md TVPTA-3(c)) -- the one exception is
`_load_backdating_mutant`, which deliberately loads a MUTATED copy of the
module source to prove the causality test methodology has power.

Every hand-built scenario below is physically valid OHLC (low <= close <=
high on every bar -- each builder asserts this itself at construction
time, per this project's documented history of tests dodging bugs via
impossible bars, see tests/test_sphinx_unicorn.py's module docstring).

Every expected value was hand-derived against the .pine source's own
logic (`docs/TradingView/pine/GC3Vxs8n-Max-script-ifvg-and-liquidity-
sweep-retest.pine`, lines 231-327) BEFORE being run, then confirmed by
reading the port's actual output -- not read off the implementation and
back-filled.
"""
import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta as ta
from pandas_ta.trend.inverse_fvg import inverse_fvg, _Fvg, _Ifvg


# ---------------------------------------------------------------------------
# Hand-built scenarios
# ---------------------------------------------------------------------------

def _series(H, L, C):
    h = pd.Series(H, dtype=float)
    l = pd.Series(L, dtype=float)
    c = pd.Series(C, dtype=float)
    assert (l <= c).all() and (c <= h).all(), "scenario built impossible OHLC"
    return h, l, c


def _bull_fvg_scenario():
    """21 flat warmup bars (TR = 1.0 each, so ATR(14) ~ 1.09 and the
    default 0.3 multiplier puts the gap threshold at ~0.33), then:

      bar 21  bridge bar up
      bar 22  GAP BAR: low 101.5 > high[20] 100.5, gap 1.0 > threshold
              -> BULLISH FVG, bottom=100.5, top=101.5, start_index=20
      bar 25  close 100.0 < bottom 100.5 -> INVERSION -> BEARISH IFVG
              (resistance), centerline (100.5+101.5)/2 = 101.0
      bar 28  close 101.9 > top 101.5 -> MITIGATED

    Returns (high, low, close, gap_bar, start_index, confirm_bar,
    mitigate_bar).
    """
    H, L, C = [], [], []
    for _ in range(21):
        H.append(100.5); L.append(99.5); C.append(100.0)
    H.append(101.6); L.append(100.4); C.append(101.0)   # 21 bridge
    H.append(102.5); L.append(101.5); C.append(102.0)   # 22 gap bar
    H.append(102.2); L.append(100.8); C.append(101.2)   # 23
    H.append(101.8); L.append(100.7); C.append(101.0)   # 24
    H.append(101.2); L.append(99.8);  C.append(100.0)   # 25 inversion
    H.append(100.6); L.append(99.6);  C.append(100.2)   # 26
    H.append(101.0); L.append(100.0); C.append(100.5)   # 27
    H.append(102.0); L.append(100.4); C.append(101.9)   # 28 mitigation
    H.append(102.1); L.append(101.0); C.append(101.6)   # 29
    H.append(102.0); L.append(101.1); C.append(101.7)   # 30
    h, l, c = _series(H, L, C)
    return h, l, c, 22, 20, 25, 28


def _bear_fvg_scenario():
    """Exact mirror of `_bull_fvg_scenario`:

      bar 22  GAP BAR: high 98.5 < low[20] 99.5, gap 1.0 > threshold
              -> BEARISH FVG, bottom=98.5, top=99.5, start_index=20
      bar 25  close 100.0 > top 99.5 -> INVERSION -> BULLISH IFVG
              (support), centerline 99.0
      bar 28  close 98.1 < bottom 98.5 -> MITIGATED
    """
    H, L, C = [], [], []
    for _ in range(21):
        H.append(100.5); L.append(99.5); C.append(100.0)
    H.append(99.6);  L.append(98.4); C.append(99.0)     # 21 bridge
    H.append(98.5);  L.append(97.5); C.append(98.0)     # 22 gap bar
    H.append(99.2);  L.append(97.8); C.append(98.8)     # 23
    H.append(99.3);  L.append(98.2); C.append(99.0)     # 24
    H.append(100.2); L.append(98.8); C.append(100.0)    # 25 inversion
    H.append(100.4); L.append(99.4); C.append(99.8)     # 26
    H.append(100.0); L.append(99.0); C.append(99.5)     # 27
    H.append(99.4);  L.append(98.0); C.append(98.1)     # 28 mitigation
    H.append(99.0);  L.append(98.0); C.append(98.5)     # 29
    H.append(99.2);  L.append(98.3); C.append(98.7)     # 30
    h, l, c = _series(H, L, C)
    return h, l, c, 22, 20, 25, 28


def _large_realistic_ohlcv(n=500, seed=42):
    """Trending random walk with non-flat, asymmetric wicks -- the
    reachability fixture. Not hand-derived; used only for "does this
    column ever fire" and monotonicity claims."""
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0006, 0.018, n)))
    open_ = np.concatenate([[close[0]], close[:-1]])
    high = np.maximum(open_, close) + np.abs(rng.normal(0, 0.9, n))
    low = np.minimum(open_, close) - np.abs(rng.normal(0, 0.9, n))
    return _series(high, low, close)


# ---------------------------------------------------------------------------
# Hand-computed correctness
# ---------------------------------------------------------------------------

def test_bull_fvg_inverts_to_bear_ifvg():
    h, l, c, gap_bar, start_index, confirm, mitigate = _bull_fvg_scenario()
    out = inverse_fvg(h, l, c)

    conf_bear = out["IFVG_CONF_BEAR_14"]
    # fires exactly on the inversion bar, nowhere else in this scenario
    assert conf_bear.iloc[confirm] == 1
    assert conf_bear.drop(index=confirm).sum() == 0
    # never back-dated to the gap bar or the gap's origin bar
    assert conf_bear.iloc[gap_bar] == 0
    assert conf_bear.iloc[start_index] == 0
    # the opposite polarity never fires here
    assert out["IFVG_CONF_BULL_14"].sum() == 0

    # centerline (100.5 + 101.5)/2 = 101.0, close 100.0 -> +1.0%
    assert out["IFVG_DIST_RES_14"].iloc[confirm] == pytest.approx(1.0)
    # not populated before confirmation
    assert out["IFVG_DIST_RES_14"].iloc[:confirm].isna().all()
    # still tracked while unmitigated (close 100.2 -> (101.0-100.2)/100.2)
    assert out["IFVG_DIST_RES_14"].iloc[confirm + 1] == pytest.approx(0.8 / 100.2 * 100)
    # support side never populated in this bearish-zone scenario
    assert out["IFVG_DIST_SUP_14"].isna().all()

    mit_bear = out["IFVG_MIT_BEAR_14"]
    assert mit_bear.iloc[mitigate] == 1
    assert mit_bear.drop(index=mitigate).sum() == 0
    assert out["IFVG_MIT_BULL_14"].sum() == 0
    # a mitigated zone stops contributing to the distance column
    assert out["IFVG_DIST_RES_14"].iloc[mitigate:].isna().all()


def test_bear_fvg_inverts_to_bull_ifvg():
    h, l, c, gap_bar, start_index, confirm, mitigate = _bear_fvg_scenario()
    out = inverse_fvg(h, l, c)

    conf_bull = out["IFVG_CONF_BULL_14"]
    assert conf_bull.iloc[confirm] == 1
    assert conf_bull.drop(index=confirm).sum() == 0
    assert conf_bull.iloc[gap_bar] == 0
    assert conf_bull.iloc[start_index] == 0
    assert out["IFVG_CONF_BEAR_14"].sum() == 0

    # centerline (98.5 + 99.5)/2 = 99.0, close 100.0 -> +1.0%
    assert out["IFVG_DIST_SUP_14"].iloc[confirm] == pytest.approx(1.0)
    assert out["IFVG_DIST_SUP_14"].iloc[:confirm].isna().all()
    assert out["IFVG_DIST_RES_14"].isna().all()

    mit_bull = out["IFVG_MIT_BULL_14"]
    assert mit_bull.iloc[mitigate] == 1
    assert mit_bull.drop(index=mitigate).sum() == 0
    assert out["IFVG_MIT_BEAR_14"].sum() == 0
    assert out["IFVG_DIST_SUP_14"].iloc[mitigate:].isna().all()


def test_volatility_filter_rejects_a_subthreshold_gap():
    """Same bull scenario, but the gap is shrunk to 0.1 -- below the
    ~0.33 threshold (ATR ~1.09 * 0.3). No FVG is detected, so no
    inversion can ever be confirmed. With `vol_mult=0` the identical
    frame DOES confirm, proving the difference is the filter and not the
    geometry."""
    h, l, c, _, _, confirm, _ = _bull_fvg_scenario()
    l = l.copy(); h = h.copy(); c = c.copy()
    l.iloc[22] = 100.6      # gap now 100.6 - 100.5 = 0.1 < threshold
    h.iloc[22] = 102.5
    assert (l <= c).all() and (c <= h).all()

    filtered = inverse_fvg(h, l, c)
    assert filtered["IFVG_CONF_BEAR_14"].sum() == 0
    assert filtered["IFVG_CONF_BULL_14"].sum() == 0

    unfiltered = inverse_fvg(h, l, c, vol_mult=0.0)
    assert unfiltered["IFVG_CONF_BEAR_14"].iloc[confirm] == 1


def test_gap_exactly_at_threshold_is_rejected_strict_inequality():
    """The source's test is `gapSize > threshold`, strictly. A gap sized
    to EXACTLY the threshold must NOT be admitted.

    The threshold is moved via `vol_mult`, not by editing `low[22]` --
    editing the gap bar's own low changes that bar's True Range and hence
    `ATR[22]`, which is the threshold's other factor, making the target a
    moving one. `vol_mult` is the only knob that shifts the threshold
    without touching the price series. The equality is EXACT in IEEE
    doubles here, asserted below rather than assumed: `ATR[22] * (gap /
    ATR[22]) == gap` for these particular values."""
    h, l, c, _, _, confirm, _ = _bull_fvg_scenario()
    from pandas_ta.volatility.atr import atr
    atr22 = atr(h, l, c, length=14).iloc[22]
    gap = l.iloc[22] - h.iloc[20]
    vm = gap / atr22
    assert atr22 * vm == gap, "float round-trip not exact -- this test needs new numbers"

    assert inverse_fvg(h, l, c, vol_mult=vm)["IFVG_CONF_BEAR_14"].sum() == 0
    # a hair below the equality point does admit it
    assert inverse_fvg(h, l, c, vol_mult=vm * (1 - 1e-12))["IFVG_CONF_BEAR_14"].iloc[confirm] == 1


def test_unmitigated_zone_keeps_reporting_distance_until_mitigation():
    h, l, c, _, _, confirm, mitigate = _bull_fvg_scenario()
    out = inverse_fvg(h, l, c)
    live = out["IFVG_DIST_RES_14"].iloc[confirm:mitigate]
    assert live.notna().all()
    assert (live > 0).all()


# ---------------------------------------------------------------------------
# Reachability + parameter behaviour on realistic synthetic data
# ---------------------------------------------------------------------------

def test_all_six_columns_fire_on_realistic_data():
    h, l, c = _large_realistic_ohlcv()
    out = inverse_fvg(h, l, c)
    assert list(out.columns) == [
        "IFVG_CONF_BULL_14", "IFVG_CONF_BEAR_14",
        "IFVG_MIT_BULL_14", "IFVG_MIT_BEAR_14",
        "IFVG_DIST_SUP_14", "IFVG_DIST_RES_14",
    ]
    for col in ("IFVG_CONF_BULL_14", "IFVG_CONF_BEAR_14",
                "IFVG_MIT_BULL_14", "IFVG_MIT_BEAR_14"):
        assert out[col].sum() > 0, f"{col} never fires -- unreachable column"
    for col in ("IFVG_DIST_SUP_14", "IFVG_DIST_RES_14"):
        assert out[col].notna().sum() > 0, f"{col} never populated"


def test_distance_columns_are_nonnegative_when_populated():
    h, l, c = _large_realistic_ohlcv()
    out = inverse_fvg(h, l, c)
    for col in ("IFVG_DIST_SUP_14", "IFVG_DIST_RES_14"):
        vals = out[col].dropna()
        assert len(vals) > 0
        assert (vals >= 0).all(), f"{col} went negative -- side constraint broken"


def test_vol_mult_monotonically_reduces_confirmations():
    h, l, c = _large_realistic_ohlcv()
    counts = []
    for vm in (0.0, 0.3, 1.5):
        out = inverse_fvg(h, l, c, vol_mult=vm)
        counts.append(int(out["IFVG_CONF_BULL_14"].sum() + out["IFVG_CONF_BEAR_14"].sum()))
    assert counts[0] > counts[1] > counts[2]
    assert counts[2] == 0


def test_max_ifvg_caps_the_tracked_pool():
    """`max_ifvg` is a FIFO cap on CONFIRMED zones, so it cannot change
    how many inversions are confirmed -- only how many stay tracked (and
    therefore how many bars carry a distance value, and how many zones
    survive long enough to be mitigated). `max_ifvg=1` reproduces the
    source's own default."""
    h, l, c = _large_realistic_ohlcv()
    one = inverse_fvg(h, l, c, max_ifvg=1)
    ten = inverse_fvg(h, l, c, max_ifvg=10)
    for col in ("IFVG_CONF_BULL_14", "IFVG_CONF_BEAR_14"):
        assert one[col].sum() == ten[col].sum()
    for col in ("IFVG_DIST_SUP_14", "IFVG_DIST_RES_14"):
        assert one[col].notna().sum() < ten[col].notna().sum()
    for col in ("IFVG_MIT_BULL_14", "IFVG_MIT_BEAR_14"):
        assert one[col].sum() <= ten[col].sum()


def test_max_fvg_age_expires_an_uninverted_gap():
    """A detected FVG that never inverts is dropped once it is older than
    `max_fvg_age` bars. Setting the cap to 1 bar means the gap detected
    at bar 22 (start_index 20, age 2) is expired on its own detection
    bar, so the bar-25 inversion can never be confirmed."""
    h, l, c, _, _, confirm, _ = _bull_fvg_scenario()
    assert inverse_fvg(h, l, c)["IFVG_CONF_BEAR_14"].iloc[confirm] == 1
    aged = inverse_fvg(h, l, c, max_fvg_age=1)
    assert aged["IFVG_CONF_BEAR_14"].sum() == 0


# ---------------------------------------------------------------------------
# CAUSALITY
# ---------------------------------------------------------------------------

def test_truncation_matches_prefix_of_full_series():
    """Computing on df[:k] must equal the first k rows of computing on
    the full series, for several k. This is prefix stability -- necessary
    for causality, but NOT sufficient on its own to catch back-dating
    (see `test_truncation_before_confirmation_catches_backdating_mutant`
    for the test that actually has that power)."""
    h, l, c = _large_realistic_ohlcv()
    full = inverse_fvg(h, l, c)
    for k in (120, 240, 333, 480):
        part = inverse_fvg(h.iloc[:k], l.iloc[:k], c.iloc[:k])
        pd.testing.assert_frame_equal(part, full.iloc[:k], check_exact=False)


def test_mutation_after_cutoff_does_not_change_earlier_output():
    h, l, c = _large_realistic_ohlcv()
    base = inverse_fvg(h, l, c)
    k = 300
    h2, l2, c2 = h.copy(), l.copy(), c.copy()
    c2.iloc[k:] = c2.iloc[k:] * 3.0
    h2.iloc[k:] = h2.iloc[k:] * 3.0
    l2.iloc[k:] = l2.iloc[k:] * 3.0
    mutated = inverse_fvg(h2, l2, c2)
    pd.testing.assert_frame_equal(mutated.iloc[:k], base.iloc[:k], check_exact=False)


def _load_backdating_mutant():
    """Loads a MUTATED copy of the real module: the two confirmation
    write-sites `conf_bear[t] = 1` / `conf_bull[t] = 1` are textually
    replaced with `conf_bear[item.start_index] = 1` /
    `conf_bull[item.start_index] = 1`, i.e. the flag is back-dated to the
    gap's own origin bar -- exactly the mistranslation the source's
    `box.new(item.startIndex, ...)` invites, since the source DOES draw
    its zone rectangle back to that bar.

    Source is read from the real module's `__file__` via `importlib` and
    exec'd into an in-memory `types.ModuleType` (no filesystem
    footprint), never hand-reimplemented -- so the mutant is provably the
    real algorithm plus one changed index.
    """
    import importlib
    import types

    # `pandas_ta.trend.inverse_fvg` as an attribute resolves to the
    # FUNCTION (re-exported by `pandas_ta/trend/__init__.py`); the dotted
    # `import_module` path gets the actual SUBMODULE, which has a real
    # `__file__`.
    real_module = importlib.import_module("pandas_ta.trend.inverse_fvg")
    with open(real_module.__file__, "r", encoding="utf-8") as fh:
        src = fh.read()
    m_bear, m_bull = "conf_bear[t] = 1", "conf_bull[t] = 1"
    assert src.count(m_bear) == 1 and src.count(m_bull) == 1, \
        "write-site markers moved or duplicated -- update this mutant loader"
    mutated = src.replace(m_bear, "conf_bear[item.start_index] = 1", 1)
    mutated = mutated.replace(m_bull, "conf_bull[item.start_index] = 1", 1)
    assert mutated != src

    mod = types.ModuleType("inverse_fvg_backdating_mutant")
    exec(compile(mutated, "<inverse_fvg_backdating_mutant>", "exec"), mod.__dict__)
    return mod.inverse_fvg


@pytest.mark.parametrize("builder,col", [
    (_bull_fvg_scenario, "IFVG_CONF_BEAR_14"),
    (_bear_fvg_scenario, "IFVG_CONF_BULL_14"),
])
def test_truncation_before_confirmation_catches_backdating_mutant(builder, col):
    """Truncate BEFORE the confirmation bar, so only the FULL run can
    ever reach the inversion and write a back-dated flag at the gap's
    origin bar. Proven two ways on the same fixture and cutoff:

    1. The REAL port writes 0 at `start_index` in BOTH runs -- no
       divergence, matching the module docstring's CAUSALITY claim.
    2. The MUTANT writes 1 at `start_index` in its FULL run (proving it
       is live, not a no-op) and 0 in its TRUNCATED run -- a genuine,
       detected divergence, which is what gives this cutoff its power.
       A cutoff placed AFTER the confirmation bar (as in
       `test_truncation_matches_prefix_of_full_series`) would let both
       runs reach the same event and back-date identically, detecting
       nothing.

    Parametrized over BOTH write-sites: the mutant patches `conf_bear`
    and `conf_bull` alike, so asserting on only one would leave the other
    patched-but-unexercised.
    """
    h, l, c, _, start_index, confirm, _ = builder()
    cut = confirm - 2                      # 23 bars >= the module's min_len of 14
    assert cut > start_index and cut < confirm

    real_full = inverse_fvg(h, l, c)
    real_trunc = inverse_fvg(h.iloc[:cut], l.iloc[:cut], c.iloc[:cut])
    assert real_full[col].iloc[start_index] == 0
    assert real_trunc[col].iloc[start_index] == 0

    mutant = _load_backdating_mutant()
    mut_full = mutant(h, l, c)
    mut_trunc = mutant(h.iloc[:cut], l.iloc[:cut], c.iloc[:cut])
    assert mut_full[col].iloc[start_index] == 1, "mutant is a no-op -- test has no power"
    assert mut_trunc[col].iloc[start_index] == 0
    assert mut_full[col].iloc[start_index] != mut_trunc[col].iloc[start_index]


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kwargs", [
    {"atr_len": 0}, {"atr_len": -3}, {"atr_len": 3.5}, {"atr_len": float("nan")},
    {"atr_len": float("inf")}, {"atr_len": True}, {"atr_len": "abc"},
    {"max_fvg_age": 0}, {"max_fvg_age": -1}, {"max_fvg_age": 2.5},
    {"max_ifvg": 0}, {"max_ifvg": -5}, {"max_ifvg": 1.5},
    {"vol_mult": -0.1}, {"vol_mult": float("nan")}, {"vol_mult": float("inf")},
    {"vol_mult": True}, {"vol_mult": "abc"},
])
def test_bad_kwargs_raise(kwargs):
    h, l, c = _large_realistic_ohlcv(n=60)
    with pytest.raises(ValueError):
        inverse_fvg(h, l, c, **kwargs)


def test_numeric_strings_are_coerced_not_rejected():
    """Documenting the INHERITED contract of `_validated_int`/
    `_validated_float` (duplicated verbatim from `bdi4kewl.py`): they
    reject NaN/inf/non-integral/bool explicitly, but a numeric STRING
    still goes through `int()`/`float()` and is accepted. Asserted here
    so the behaviour is a recorded decision rather than an untested
    assumption -- `"abc"` (used in the rejection table above) does raise."""
    h, l, c = _large_realistic_ohlcv(n=120)
    from_str = inverse_fvg(h, l, c, atr_len="20", vol_mult="0.5")
    from_num = inverse_fvg(h, l, c, atr_len=20, vol_mult=0.5)
    pd.testing.assert_frame_equal(from_str, from_num)


@pytest.mark.parametrize("kwargs", [
    {}, {"atr_len": None}, {"vol_mult": None}, {"max_fvg_age": None}, {"max_ifvg": None},
    {"atr_len": 20, "vol_mult": 0, "max_fvg_age": 50, "max_ifvg": 3},
])
def test_good_kwargs_accepted(kwargs):
    h, l, c = _large_realistic_ohlcv(n=120)
    out = inverse_fvg(h, l, c, **kwargs)
    assert out is not None and len(out) == 120


def test_atr_len_suffixes_the_column_names():
    h, l, c = _large_realistic_ohlcv(n=120)
    out = inverse_fvg(h, l, c, atr_len=20)
    assert "IFVG_CONF_BULL_20" in out.columns
    assert out.name == "IFVG_20"
    assert out.category == "trend"


def test_too_short_series_returns_none():
    h, l, c = _large_realistic_ohlcv(n=10)
    assert inverse_fvg(h, l, c) is None


# ---------------------------------------------------------------------------
# Offset + accessor
# ---------------------------------------------------------------------------

def test_offset_shifts_every_column():
    h, l, c = _large_realistic_ohlcv(n=200)
    base = inverse_fvg(h, l, c)
    shifted = inverse_fvg(h, l, c, offset=2)
    for col in base.columns:
        pd.testing.assert_series_equal(
            shifted[col].iloc[2:].reset_index(drop=True),
            base[col].iloc[:-2].reset_index(drop=True),
            check_names=False, check_dtype=False)


def test_dataframe_accessor():
    h, l, c = _large_realistic_ohlcv(n=200)
    df = pd.DataFrame({"high": h, "low": l, "close": c})
    out = df.ta.inverse_fvg()
    assert out.shape == (200, 6)
    assert "IFVG_DIST_RES_14" in out.columns


def test_registered_in_trend_category():
    assert "inverse_fvg" in ta.Category["trend"]


# ---------------------------------------------------------------------------
# Internal state objects
# ---------------------------------------------------------------------------

def test_state_objects_are_slotted():
    f = _Fvg(101.5, 100.5, 20, True)
    i = _Ifvg(101.5, 100.5, False)
    assert (f.top, f.bottom, f.start_index, f.is_bull) == (101.5, 100.5, 20, True)
    assert (i.top, i.bottom, i.is_bull, i.mitigated) == (101.5, 100.5, False, False)
    with pytest.raises(AttributeError):
        f.extra = 1
    with pytest.raises(AttributeError):
        i.extra = 1
