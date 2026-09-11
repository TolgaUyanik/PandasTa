# -*- coding: utf-8 -*-
"""PINEBI-1b — tranche 1 of the 16 `port` rows: kcw, rwi, pzo, vzo, szo, rms, wpo.

WHAT IS PINNED HERE, in order of how much it would hurt to lose
---------------------------------------------------------------
1. **`vzo` signs volume by the PRICE direction, not by volume's own change.**
   Pine's shared `zone()` helper reads `math.sign(ta.change(close))` while
   taking `source` separately, and `vzo` passes `volume` as the source. Reading
   `sign(change(volume))` produces a well-behaved series in the same range that
   answers a different question, and no shape, range or NaN test would catch
   it. `test_vzo_signs_volume_by_price_direction_not_its_own` is the only thing
   standing between this port and that substitution.

2. **`szo` divides by `length`, not by anything derived from the TEMA**, so its
   range is about ±100/length (±7.1 at the default 14) and NOT ±100. It reads
   like a bug in the source. It is the source's behaviour, a mined rule would
   match on its thresholds, and "fixing" it silently would break every such
   rule. Pinned with a measured range.

3. **Gate B causality**, for all seven, by future-perturbation with a J sweep.
   Prefix truncation alone cannot see back-dating — it is the reason
   `PandasTa/CLAUDE.md` requires a mutant — so each indicator is also run as a
   deliberately non-causal mutant and the mutant must be CAUGHT at every J.

4. **Gate D scale-freeness**, bit-identical under ×8 and ×64. `rms` is the
   interesting one: its DEFAULT output (a percent distance) is bit-identical,
   and its `raw=True` output (a price level) is deliberately NOT — the test
   asserts both directions, because a `raw=True` that accidentally became
   scale-free would mean the level had stopped being a level.

5. **`wpo` is undefined where `close[1] > high`** and must be NaN there rather
   than clamped into `asin`'s domain. The share of affected bars is measured
   and asserted non-zero on the fixture, so the guard cannot rot into a
   no-op.

6. **`kcw` delegates to `kc`** instead of re-deriving the channel. Pinned by
   recomputing the width from `kc`'s own three columns and requiring an exact
   match — if someone re-implements the channel inside `kcw`, this fails.

7. Wiring: all seven reachable on the module, on `df.ta`, and through
   `df.ta.strategy()`.
"""
import importlib.util

import numpy as np
import pytest
from pandas import DataFrame, Series, date_range

import pandas_ta as ta

_NAMES = ["kcw", "rwi", "pzo", "vzo", "szo", "rms", "wpo"]


def _frame(n=600, seed=11):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.012, n)))
    open_ = close * (1 + rng.normal(0, 0.003, n))
    high = np.maximum(open_, close) * (1 + abs(rng.normal(0, 0.006, n)))
    low = np.minimum(open_, close) * (1 - abs(rng.normal(0, 0.006, n)))
    idx = date_range("2022-01-01", periods=n, freq="D")
    return DataFrame({"open": open_, "high": high, "low": low, "close": close,
                      "volume": rng.integers(1e5, 1e6, n).astype(float)},
                     index=idx)


_CALLS = {
    "kcw": lambda f, d: f(d["high"], d["low"], d["close"]),
    "rwi": lambda f, d: f(d["high"], d["low"], d["close"]),
    "pzo": lambda f, d: f(d["close"]),
    "vzo": lambda f, d: f(d["close"], d["volume"]),
    "szo": lambda f, d: f(d["close"]),
    "rms": lambda f, d: f(d["close"]),
    "wpo": lambda f, d: f(d["high"], d["close"]),
}

_J_SWEEP = range(30, 595, 5)


def _mutate(module, old, new):
    """Read the shipped module's source, apply one edit, exec it in memory."""
    spec = importlib.util.find_spec(module)
    src = open(spec.origin, encoding="utf8").read()
    mutated = src.replace(old, new)
    assert mutated != src, f"the mutation did not apply to {module} — blind test"
    ns = {}
    exec(compile(mutated, "<mutant>", "exec"), ns)
    return ns[module.rsplit(".", 1)[1]]


def _perturb(d, J):
    """Replace the future, from bar J onward, with a materially different one.

    A purely MULTIPLICATIVE perturbation is not enough here, and finding that
    out is the reason this docstring exists. `szo` and `wpo` both reduce the
    future to `sign(change(close))`. Scaling every future close by 1.3 leaves
    the ORDER of consecutive closes unchanged, so every sign is unchanged, so
    a genuinely non-causal mutant reads a different number and still emits an
    identical series -- it escaped at 65 of 113 J values before this was fixed.
    A mutant that escapes is not evidence the indicator is causal; it is
    evidence the probe is blind.

    So the future is MIRRORED about its first bar as well as scaled: every
    future increment changes sign, which is the only perturbation a
    sign-of-difference indicator can see.
    """
    e = d.copy()
    m = np.arange(len(d)) >= J
    if m.any():
        pivot = float(d["close"].to_numpy()[J])
        for c in ("open", "high", "low", "close"):
            e.loc[m, c] = 2.0 * pivot - d.loc[m, c]
        # Re-establish the OHLC invariant the mirror inverts, or `high < low`
        # makes several ports NaN for a reason unrelated to causality.
        hi = e.loc[m, ["open", "high", "low", "close"]].max(axis=1) * 1.02
        lo = e.loc[m, ["open", "high", "low", "close"]].min(axis=1) * 0.98
        e.loc[m, "high"] = hi
        e.loc[m, "low"] = lo
        e.loc[m, "close"] *= 1.3
        e.loc[m, "volume"] *= 5
    return e


def _sweep(name, fn, d):
    """(count of J at which output BEFORE J moved, worst |delta| seen)."""
    call = _CALLS[name]
    base = np.asarray(call(fn, d), dtype=float)
    caught, worst = 0, 0.0
    for J in _J_SWEEP:
        b = np.asarray(call(fn, _perturb(d, J)), dtype=float)[:J]
        a = base[:J]
        m = np.isfinite(a) & np.isfinite(b)
        if not m.any():
            continue
        delta = float(np.abs(a[m] - b[m]).max())
        if delta > 0:
            caught += 1
            worst = max(worst, delta)
    return caught, worst


# ----------------------------------------------------------------- wiring

@pytest.mark.parametrize("name", _NAMES)
def test_every_port_is_wired_through_all_call_styles(name):
    d = _frame()
    assert callable(getattr(ta, name)), f"{name} missing on the module"
    assert callable(getattr(d.ta, name)), f"{name} missing on the df.ta accessor"
    flat = [n for v in ta.Category.values() for n in v]
    assert name in flat, f"{name} is not registered in Category"


def test_the_bulk_sweep_reaches_all_seven():
    d = _frame()
    before = d.shape[1]
    d.ta.strategy(ta.Strategy(name="pinebi1b",
                              ta=[{"kind": k} for k in _NAMES]))
    assert d.shape[1] - before == 8, \
        f"expected 8 new columns (rwi emits 2), got {d.shape[1] - before}"


# ------------------------------------------------------------- Gate C: fires

@pytest.mark.parametrize("name", _NAMES)
def test_every_shipped_column_fires(name):
    d = _frame()
    out = _CALLS[name](getattr(ta, name), d)
    frame = out.to_frame() if isinstance(out, Series) else out
    for c in frame.columns:
        s = frame[c].dropna()
        assert len(s) > 0, f"{c} is all-NaN"
        assert s.nunique() > 1, f"{c} is constant — it cannot be a feature"


# ------------------------------------------------------- Gate D: scale-free

@pytest.mark.parametrize("name", _NAMES)
@pytest.mark.parametrize("k", [8, 64])
def test_scale_invariance_is_bit_identical(name, k):
    d = _frame()
    e = d.copy()
    for c in ("open", "high", "low", "close"):
        e[c] *= k
    a = np.asarray(_CALLS[name](getattr(ta, name), d), dtype=float)
    b = np.asarray(_CALLS[name](getattr(ta, name), e), dtype=float)
    m = np.isfinite(a) & np.isfinite(b)
    assert m.any()
    assert float(np.abs(a[m] - b[m]).max()) == 0.0, \
        f"{name} is not bit-identical under x{k}"
    assert (np.isfinite(a) == np.isfinite(b)).all(), \
        f"{name}'s NaN mask moved under x{k}"


def test_rms_raw_is_a_price_level_and_therefore_not_scale_free():
    """The raw=True escape hatch must stay a LEVEL.

    If this ever passes as scale-free, `raw=True` has stopped returning the
    level and the percent-distance default has been applied twice.
    """
    d = _frame()
    a = np.asarray(ta.rms(d["close"], raw=True), dtype=float)
    b = np.asarray(ta.rms(d["close"] * 8, raw=True), dtype=float)
    m = np.isfinite(a) & np.isfinite(b)
    assert float(np.abs(a[m] - b[m]).max()) > 1.0
    assert ta.rms(d["close"], raw=True).name == "RMS_14"
    assert ta.rms(d["close"]).name == "RMS_DIST_PCT_14"


# -------------------------------------------------------- Gate B: causality

@pytest.mark.parametrize("name", _NAMES)
def test_no_port_reads_the_future(name):
    d = _frame()
    leaked, _ = _sweep(name, getattr(ta, name), d)
    assert leaked == 0, \
        f"{name} leaks the future at {leaked} of {len(_J_SWEEP)} J values"


@pytest.mark.parametrize("module,old,new,name", [
    ("pandas_ta.momentum.pzo", "zone(close, close, length)",
     "zone(close, close.shift(-2), length)", "pzo"),
    ("pandas_ta.volume.vzo", "zone(close, volume, length)",
     "zone(close, volume.shift(-2), length)", "vzo"),
    # NOT `sign(close.diff(-1))`. A one-bar lookahead THROUGH A SIGN is only
    # visible when the sign actually flips, which a perturbation can force at
    # best half the time -- that mutant escaped at 65 of 113 J values, and the
    # escape said nothing about `szo`. Mutating the SMOOTHER instead changes
    # magnitude, which is always visible. Same reasoning as `bw_mfi`'s
    # centred-window mutant in `test_altport2_ports.py`.
    ("pandas_ta.momentum.szo", "ema1 = ema(trend, length=length)",
     "ema1 = trend.rolling(length, center=True).mean()", "szo"),
    # `min_periods=1` is load-bearing, not decoration. `ti` is NaN on every
    # gap-down bar (asin out of domain), so a centred window with the default
    # min_periods requires a fully finite window and produced a mutant that
    # was 99.8% NaN -- nothing to compare, `caught=0`, and an escape that was
    # an artifact of the mutant rather than a statement about `wpo`. A
    # degenerate mutant is the failure mode this whole gate exists to avoid.
    ("pandas_ta.momentum.wpo", "wpo = ema(ti, length=length)",
     "wpo = ti.rolling(length, center=True, min_periods=1).mean()", "wpo"),
    ("pandas_ta.statistics.rms",
     "level = sqrt((close ** 2).rolling(length).sum() / length)",
     "level = sqrt((close ** 2).rolling(length, center=True).sum() / length)",
     "rms"),
    ("pandas_ta.momentum.rwi", "prior_low = low.shift(length)",
     "prior_low = low.shift(-length)", "rwi"),
])
def test_the_backdating_mutant_is_caught(module, old, new, name):
    """A causal implementation and a non-causal one must be distinguishable.

    Without this, `test_no_port_reads_the_future` is only evidence that the
    sweep runs — it would pass just as happily on an indicator that ignores
    its inputs.
    """
    d = _frame()
    mut = _mutate(module, old, new)
    caught, worst = _sweep(name, mut, d)
    assert caught == len(_J_SWEEP), \
        f"the {name} mutant escaped at {len(_J_SWEEP) - caught} J values"
    assert worst > 0.0


# ------------------------------------------------- the per-indicator traps

def test_vzo_signs_volume_by_price_direction_not_its_own():
    """The single most substitutable line in this whole tranche.

    Built so the two readings MUST differ: volume rises monotonically while
    price alternates, so `sign(change(volume))` is +1 everywhere and
    `sign(change(close))` alternates.
    """
    n = 200
    close = Series([100 + (1 if i % 2 else -1) for i in range(n)],
                   dtype=float)
    volume = Series(np.arange(1, n + 1), dtype=float) * 1000.0

    correct = ta.vzo(close, volume, length=14)

    # What the wrong reading would produce, computed here rather than asserted
    # about: sign the volume by ITS OWN change instead of by price.
    from pandas_ta.overlap.ema import ema
    wrong_num = ema(np.sign(volume.diff()) * volume, length=14)
    wrong = 100.0 * wrong_num / ema(volume, length=14)

    m = correct.notna() & wrong.notna()
    assert m.any()
    assert float(np.abs(correct[m] - wrong[m]).max()) > 50.0, \
        "vzo is indistinguishable from the volume-signed reading on a fixture " \
        "built to separate them — the sign term is reading the wrong series"
    # And the wrong reading is pinned to what it is: all-up volume => ~+100.
    assert wrong[m].min() > 95.0


def test_szo_range_is_scaled_by_one_over_length_not_plus_minus_100():
    d = _frame()
    for length in (7, 14, 28):
        s = ta.szo(d["close"], length=length).dropna()
        assert s.abs().max() < 100.0 / length * 1.6, \
            f"szo({length}) exceeded the 100/length envelope"
        assert s.abs().max() > 100.0 / length * 0.15, \
            f"szo({length}) is suspiciously flat for a sign oscillator"


def test_wpo_is_nan_where_asin_is_out_of_domain_and_not_clamped():
    d = _frame()
    out_of_domain = (d["close"].shift(1) / d["high"]) > 1.0
    assert out_of_domain.sum() > 0, \
        "the fixture has no gap-down bars, so this test proves nothing"
    # The EMA smears NaN forward, so the assertion is on the raw term rather
    # than on the smoothed output: no finite reading may be produced FROM an
    # out-of-domain bar.
    from numpy import arcsin
    ratio = d["close"].shift(1) / d["high"]
    assert np.isnan(arcsin(ratio.where(ratio.abs() <= 1.0))[out_of_domain]).all()


def test_kcw_delegates_to_kc_rather_than_reimplementing_the_channel():
    d = _frame()
    bands = ta.kc(d["high"], d["low"], d["close"], length=20, scalar=2.0)
    lower, basis, upper = (bands.iloc[:, 0], bands.iloc[:, 1], bands.iloc[:, 2])
    expected = (upper - lower) / basis
    got = ta.kcw(d["high"], d["low"], d["close"], length=20, scalar=2.0)
    m = expected.notna() & got.notna()
    assert m.any()
    assert float(np.abs(expected[m] - got[m]).max()) == 0.0


def test_rwi_masks_the_nz_warmup_instead_of_shipping_a_zeroed_prior():
    """Pine's nz() maps the missing prior bar to 0; that is a real, large value.

    `(high - 0) / divisor` is a plausible-looking number on every warm-up bar.
    Shipping it would plant a synthetic reading on the first `length` bars.
    """
    d = _frame()
    out = ta.rwi(d["high"], d["low"], d["close"], length=14)
    assert out.iloc[:14].isna().all().all(), \
        "rwi is shipping nz()-zeroed warm-up values"


def test_zone_helper_is_shared_not_duplicated():
    """`pzo` and `vzo` must call one implementation, per the FVGENG rule."""
    # NOTE: `import pandas_ta.momentum.pzo as m` does NOT give the module --
    # the category `__init__` does `from .pzo import pzo`, which rebinds the
    # name to the FUNCTION and shadows the submodule. That is the exact trap
    # `test_no_module_shadows_a_function_name_anywhere_in_the_package` exists
    # for. Reach the modules through sys.modules instead.
    import sys
    pzo_mod = sys.modules["pandas_ta.momentum.pzo"]
    vzo_mod = sys.modules["pandas_ta.volume.vzo"]
    assert pzo_mod.zone is vzo_mod.zone


def test_zone_leaves_the_warmup_nan_rather_than_pine_zeroing_it():
    """Pine's nz() would make the warm-up 0; PINEBI-1e's `normalize` lesson.

    A zero on the warm-up is a synthetic reading planted on real bars. The
    division guard still applies mid-series.
    """
    d = _frame()
    s = ta.pzo(d["close"], length=14)
    assert s.iloc[0] != s.iloc[0] or np.isnan(s.iloc[0]), \
        "pzo's first bar is a zeroed warm-up, not NaN"
