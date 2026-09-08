# -*- coding: utf-8 -*-
"""TALIB-1: the ten `port` rows of `../AlternativeRepos/altrepo_talib.csv`.

WHAT SHIPPED, AND WHAT THIS FILE PINS, in order of how much it would hurt to
lose.

**Gate A -- agreement with `talib`, measured, on real BIST daily frames.**
`talib` is an OPTIONAL dependency (`setup.py`, `extras_require["dev"]`) and the
shipped code must never import it, so every Gate A test here SKIPS when it is
absent and the fork itself is checked separately for the import
(`test_no_shipped_module_imports_talib`). The pinned numbers, over 20 frames
sampled with `random.Random(0)` from `../Backtesting/datastore/cache/*_1d.parquet`
(28,548 comparable bars for the lookback-32 family, 27,928 for the lookback-63
family):

    HT_DCPERIOD          1.3e-11      HT_DCPHASE           5.6e-10
    HT_PHASOR inphase    1.9e-13      HT_PHASOR quadrature 3.2e-13
    HT_SINE sine         6.1e-12      HT_SINE leadsine     9.7e-12
    HT_TRENDLINE         0.0          HT_TRENDMODE         0.0
    MAMA                 2.7e-06      FAMA                 2.7e-04
    SAREXT               0.0          IMI                  1.4e-14
    BETA                 4.9e-12 at the 99.8th pct, 3.4e+06 on 46 of 29,088

The two outliers are NOT formula errors and are pinned as what they are:

* MAMA/FAMA. All of it is ONE bar of one frame (`ISMEN_IS_1d` bar 2327) where
  our detrender rounds to exactly 0.0 and TA-Lib's -- which agrees with ours
  only to 1.9e-13, see HT_PHASOR -- does not. Alpha is a CLAMPED reciprocal of
  a phase difference, so that knife-edge is 0.05 against 0.5 and the recursion
  carries it forward. `test_mama_residual_is_one_knife_edge_bar` measures the
  count, so a real regression (many bars) cannot hide behind this allowance.
* BETA. 46 pooled bars of 29,088 (0.158%) exceed 1e-8, and on those the
  MEDIAN denominator `n*Sxx - Sx^2` is 1.78e-14 against 7.47e-03 on the bars
  that agree. Runs of identical highs cancel the uncentred sum of squares to
  noise and TA-Lib's own `denominator == 0` guard does not fire at 1.78e-14,
  so both sides are returning noise there. `test_beta_matches_talib` asserts
  the percentile, the SIZE of that population, and that it is still the
  ill-conditioned one.

**The two warm-ups** (`test_the_two_warmups_are_the_measured_ones`). TA-Lib
primes the price smoother for 12 bars before the lookback-32 read-outs and 37
before the lookback-63 ones. Running the lookback-63 family at 12 reproduces
`HT_DCPERIOD` EXACTLY and still leaves `HT_TRENDLINE` wrong by 0.18 and
`HT_DCPHASE` by 70 degrees -- as a decaying warm-up transient that is exactly
zero by bar ~700. A port validated only on its tail would have looked correct.
This is the single most expensive thing in this file to lose.

**The Hilbert summation order** (`test_the_hilbert_summation_order_is_load_bearing`).
`_hilbert` accumulates `-a*x[t-6] + a*x[t] - b*x[t-4] + b*x[t-2]` in TA-Lib's
order. The algebraically identical reordering is wrong by 1.1e-2 on MAMA over
`PETKM_IS_1d`, because MAMA's clamped alpha amplifies a 1-ulp difference in an
ill-conditioned `atan` into a factor of ten.

**Gate B -- causality by MUTANT, not by prefix truncation**
(`test_state_machine_is_causal_under_future_perturbation`,
`test_backdating_mutant_is_caught`). The state machine is a recursion, so
prefix truncation cannot see back-dating; the future-perturbation detector
(perturb every bar from J onward, assert nothing before J moves) is what works,
per `tests/test_pinebi_1e_utilities.py::test_pivot_is_causal_with_a_mutant`.

**Gate C -- reachability with counts** (`test_every_shipped_column_fires_on_real_data`).

**Gate D -- scale invariance** (`test_dyadic_scale_invariance`,
`test_non_dyadic_scale_invariance`). Every SHIPPED column is a ratio, an angle,
a bar count or a flag. The price levels TA-Lib emits -- `HT_TRENDLINE`,
`MAMA`, `FAMA`, `SAREXT` -- are asserted to FAIL the same test, so the claim
that they are price levels is falsifiable rather than decorative, and none of
them is registered in `Category`.

**FIVE COLUMNS WERE BUILT, WIRED, MEASURED AND DELETED ON GATE E.** They are
named here because the deletion is the deliverable, not an embarrassment:

    SAREXTd_0.02_0.2    +0.9850 vs `dist_to_psar_pct`      408,075 bars
    SAREXTs_0.02_0.2    +0.9598 vs `PSAR_Signal`           408,075 bars
    HT_TRENDLINE_DIST   +0.9576 vs `bias`                  402,646 bars
    MAMAf_0.5_0.05      +0.9408 vs `QQE_RSIMA`             405,405 bars
    MAMAd_0.5_0.05      +0.9148 vs `NWE_MID_200_8.0_8.0`   390,453 bars

`SAREXTs` is the one worth remembering. Against the engine's NUMERIC columns
it read **+0.8393** -- inside the 0.76-0.90 disclose band -- and it was about
to ship on that number. `PSAR_Signal` is an OBJECT column holding the strings
"Bullish"/"Bearish", so `select_dtypes(include=[np.number])` drops it and the
main grid never compares the new SAR direction flag with the engine's existing
SAR direction flag. Stage 4 of the harness coerces the three non-numeric stop
columns and re-measures: +0.9598. A max-rho taken over the numeric comparators
alone is a measured number that is still wrong about what it measures.

That emptied THREE indicators of features entirely. `ht_trendline`, `mama` and
`sarext` now return TA-Lib's raw price levels, are OUT of `Category`, and are
in `strategy`'s exclusion list. `test_the_reverted_columns_stay_deleted` is
the guard: it fails if any of the five reappears in a default call.

**Wiring** (`test_the_shipped_six_are_registered_and_reachable`,
`test_the_four_unswept_ports_are_reachable_but_excluded`). `beta` needs a
benchmark series a single-frame sweep cannot supply; `ht_trendline`, `mama`
and `sarext` emit price levels. All four are absent from `Category` AND
present in `strategy`'s default exclusion list -- registering such a function
took `df.ta.strategy()` down earlier in this batch.

Gate E itself is NOT pinned here: overlap against the parent engine's
485-column production output cannot run inside a unit test. It lives in
`../Backtesting/scripts/analysis/measure_talib1_overlap_full.py` and its CSVs,
and the verdicts are tabulated in `docs/TalibPortsMeasured.md`.
"""
import glob
import importlib.util
import math
import os
import random
import subprocess
import sys

import numpy as np
import pytest
from pandas import DataFrame, Series, date_range

from .context import pandas_ta  # noqa: F401

from pandas_ta.cycles import (ht_dcperiod, ht_dcphase, ht_phasor, ht_sine,
                              ht_trendmode)
from pandas_ta.cycles._hilbert import (LOOKBACK_32, LOOKBACK_63, _WARMUP_32,
                                       _WARMUP_63, ht_state)
from pandas_ta.momentum import imi
from pandas_ta.overlap import ht_trendline, mama
from pandas_ta.statistics import beta
from pandas_ta.trend import sarext

_HERE = os.path.dirname(os.path.abspath(__file__))
_FORK = os.path.dirname(_HERE)
CACHE = os.path.join(os.path.dirname(_FORK), "Backtesting", "datastore", "cache")

# The eight columns that survived Gate E and are swept into the feature set.
SHIPPED_COLUMNS = [
    "HT_DCPERIOD", "HT_DCPHASE", "HT_PHASOR_IP", "HT_PHASOR_Q",
    "HT_SINE", "HT_LEADSINE", "HT_TRENDMODE", "IMI_14",
]

# Deleted on Gate E, with the rho that killed each. Reachable only behind
# `emit_dist=True`, never from a default call.
REVERTED_COLUMNS = {
    "SAREXTd_0.02_0.2": "+0.9850 vs dist_to_psar_pct",
    "SAREXTs_0.02_0.2": "+0.9598 vs PSAR_Signal (non-numeric; stage 4)",
    "HT_TRENDLINE_DIST": "+0.9576 vs bias",
    "MAMAf_0.5_0.05": "+0.9408 vs QQE_RSIMA",
    "MAMAd_0.5_0.05": "+0.9148 vs NWE_MID_200_8.0_8.0",
}

REGISTERED = {
    "cycles": ["ht_dcperiod", "ht_dcphase", "ht_phasor", "ht_sine",
               "ht_trendmode"],
    "momentum": ["imi"],
}

# Callable as `df.ta.<name>()`, deliberately never swept.
UNSWEPT = ["beta", "ht_trendline", "mama", "sarext"]


def _talib():
    try:
        import talib
        return talib
    except ImportError:                                   # pragma: no cover
        pytest.skip("talib is an optional dev dependency and is not installed")


def _frames(k=20, seed=0):
    files = sorted(glob.glob(os.path.join(CACHE, "*_1d.parquet")))
    if len(files) < k:
        pytest.skip(f"{CACHE} has {len(files)} daily frames, need {k}")
    import pandas as pd
    out = []
    for f in random.Random(seed).sample(files, k):
        df = pd.read_parquet(f)
        df.columns = [str(c).lower() for c in df.columns]
        c = df["close"].astype(float).to_numpy()
        if len(c) < 200 or not np.isfinite(c).all() or (c <= 0).any():
            continue
        out.append((os.path.basename(f), df))
    assert out, "no usable frames"
    return out


def _one(name):
    import pandas as pd
    p = os.path.join(CACHE, name)
    if not os.path.exists(p):
        pytest.skip(f"{p} absent")
    df = pd.read_parquet(p)
    df.columns = [str(c).lower() for c in df.columns]
    return df


def _synthetic(n=600, seed=3):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    idx = date_range("2020-01-01", periods=n, freq="D")
    high = Series(close + abs(rng.normal(0, 0.8, n)), index=idx)
    low = Series(close - abs(rng.normal(0, 0.8, n)), index=idx)
    open_ = Series(close + rng.normal(0, 0.4, n), index=idx)
    return open_, high, low, Series(close, index=idx)


# --------------------------------------------------------------------------
# Gate A
# --------------------------------------------------------------------------

def _maxdiff(mine, ref, lookback):
    idx = np.arange(len(ref))
    sel = (~np.isnan(ref)) & (idx >= lookback)
    if sel.sum() == 0:
        return 0.0, 0
    d = np.abs(np.asarray(mine, dtype=float)[sel] - ref[sel])
    return float(np.nanmax(d)), int(sel.sum())


def test_the_hilbert_family_matches_talib():
    """Seven read-outs, one state machine, measured against `talib`.

    The tolerances below are the MEASURED maxima rounded up one significant
    figure, not round numbers picked for comfort. `HT_TRENDLINE` and
    `HT_TRENDMODE` are asserted at strict equality because that is what they
    measured -- 0.0 over 27,928 bars.
    """
    talib = _talib()
    tol = {
        "HT_DCPERIOD": 1e-10, "HT_PHASOR_IP": 1e-12, "HT_PHASOR_Q": 1e-12,
        "HT_DCPHASE": 1e-8, "HT_SINE": 1e-10, "HT_LEADSINE": 1e-10,
        "HT_TRENDLINE": 0.0, "HT_TRENDMODE": 0.0,
    }
    worst = {k: (0.0, 0) for k in tol}
    for _name, df in _frames():
        x = df["close"].astype(float).to_numpy()
        a = ht_state(x, _WARMUP_32)
        b = ht_state(x, _WARMUP_63)
        ip, q = talib.HT_PHASOR(x)
        sn, ls = talib.HT_SINE(x)
        pairs = [
            ("HT_DCPERIOD", a["dcperiod"], talib.HT_DCPERIOD(x), LOOKBACK_32),
            ("HT_PHASOR_IP", a["inphase"], ip, LOOKBACK_32),
            ("HT_PHASOR_Q", a["quadrature"], q, LOOKBACK_32),
            ("HT_DCPHASE", b["dcphase"], talib.HT_DCPHASE(x), LOOKBACK_63),
            ("HT_SINE", b["sine"], sn, LOOKBACK_63),
            ("HT_LEADSINE", b["leadsine"], ls, LOOKBACK_63),
            ("HT_TRENDLINE", b["trendline"], talib.HT_TRENDLINE(x), LOOKBACK_63),
            ("HT_TRENDMODE", b["trendmode"],
             talib.HT_TRENDMODE(x).astype(float), LOOKBACK_63),
        ]
        for key, mine, ref, lb in pairs:
            d, n = _maxdiff(mine, ref, lb)
            if d > worst[key][0]:
                worst[key] = (d, n)
            worst[key] = (worst[key][0], worst[key][1] + n)
    bad = {k: v for k, v in worst.items() if v[0] > tol[k]}
    assert bad == {}, f"Gate A regressions (measured, tolerance): {bad} vs {tol}"
    for k, (d, n) in worst.items():
        assert n > 10000, f"{k}: only {n} comparable bars -- the sample thinned"


def test_mama_residual_is_one_knife_edge_bar():
    """MAMA's 2.7e-6 is ONE bar, and this counts it rather than allowing it.

    A tolerance of 1e-5 with no count would also pass a port that was wrong by
    1e-6 on every bar. The measured shape is: 28,548 comparable bars, at most a
    handful above 1e-9, all of them downstream of `ISMEN_IS_1d` bar 2327 where
    our detrender rounds to exactly 0.0 and TA-Lib's does not.
    """
    talib = _talib()
    total = 0
    off_frames = []
    for name, df in _frames():
        x = df["close"].astype(float).to_numpy()
        st = ht_state(x, _WARMUP_32)
        mm, fm = talib.MAMA(x)
        idx = np.arange(len(x))
        sel = (~np.isnan(mm)) & (idx >= LOOKBACK_32)
        total += int(sel.sum())
        d = np.abs(st["mama"][sel] - mm[sel])
        if d.max() > 1e-9:
            off_frames.append((name, float(d.max())))
    assert total > 25000, f"only {total} comparable bars"
    assert len(off_frames) <= 1, (
        f"more than one frame drifts from talib's MAMA: {off_frames}. "
        f"That is a formula regression, not the known knife edge."
    )
    for _name, d in off_frames:
        assert d < 1e-4, f"knife-edge frame drifted further than measured: {d}"


def test_sarext_matches_talib_at_defaults_and_off_defaults():
    """0.0, twice. Off-default parameters are the half that finds bugs.

    Every acceleration parameter defaults to the same 0.02/0.2 pair, so a port
    that ignored `accelerationinitshort` entirely would still score 0.0 at the
    defaults. The second assertion uses an asymmetric schedule and a non-zero
    `offsetonreverse`, which is what actually exercises the parameter handling.
    """
    talib = _talib()
    worst_default, n_default = 0.0, 0
    for _name, df in _frames():
        h = df["high"].astype(float).to_numpy()
        l = df["low"].astype(float).to_numpy()
        if not (np.isfinite(h).all() and np.isfinite(l).all()):
            continue
        ref = talib.SAREXT(h, l)
        mine = sarext(df["high"].astype(float),
                      df["low"].astype(float))["SAREXT_0.02_0.2"].to_numpy()
        d, n = _maxdiff(mine, ref, 1)
        worst_default = max(worst_default, d)
        n_default += n
    assert n_default > 25000, f"only {n_default} comparable bars"
    assert worst_default == 0.0, f"SAREXT drifted at the defaults: {worst_default}"

    df = _one("GARAN_IS_1d.parquet")
    h, l = df["high"].astype(float), df["low"].astype(float)
    kw = dict(startvalue=0.0, offsetonreverse=0.05,
              accelerationinitlong=0.03, accelerationlong=0.03,
              accelerationmaxlong=0.3, accelerationinitshort=0.01,
              accelerationshort=0.01, accelerationmaxshort=0.15)
    ref = talib.SAREXT(h.to_numpy(), l.to_numpy(), **kw)
    mine = sarext(h, l, **kw)["SAREXT_0.03_0.3"].to_numpy()
    d, n = _maxdiff(mine, ref, 1)
    assert n > 6000 and d == 0.0, f"SAREXT drifted off the defaults: {d} over {n}"


def test_imi_matches_talib():
    talib = _talib()
    worst, total = 0.0, 0
    for _name, df in _frames():
        o, c = df["open"].astype(float), df["close"].astype(float)
        if not (np.isfinite(o.to_numpy()).all() and np.isfinite(c.to_numpy()).all()):
            continue
        ref = talib.IMI(o.to_numpy(), c.to_numpy(), 14)
        d, n = _maxdiff(imi(o, c).to_numpy(), ref, 14)
        worst = max(worst, d)
        total += n
    assert total > 20000, f"only {total} comparable bars"
    assert worst < 1e-10, f"IMI drifted: {worst}"


def test_beta_matches_talib():
    """Percentiles, the size of the bad population, AND what makes it bad.

    Pooled over 20 frames / 29,088 bars: median 4.4e-15, p99.8 4.9e-12, then a
    cliff -- p99.9 is 1.03. Asserting only a percentile would let the cliff
    grow; asserting only the max would fail on a port that is exactly right.
    So all three are asserted: the well-conditioned bars agree, the bad
    population stays small, and the bad population is bad FOR THE STATED
    REASON -- a denominator that has cancelled to noise, on which TA-Lib's own
    output is meaningless too.
    """
    talib = _talib()
    diffs, denoms = [], []
    for _name, df in _frames():
        h, l = df["high"].astype(float), df["low"].astype(float)
        hv, lv = h.to_numpy(), l.to_numpy()
        if not (np.isfinite(hv).all() and np.isfinite(lv).all()):
            continue
        ref = talib.BETA(hv, lv, 5)
        mine = beta(h, other=l, length=5).to_numpy()
        sel = (~np.isnan(ref)) & (~np.isnan(mine))
        diffs.append(np.abs(mine[sel] - ref[sel]))
        rx = h.pct_change()
        den = (5 * (rx * rx).rolling(5).sum() - rx.rolling(5).sum() ** 2)
        denoms.append(np.abs(den.to_numpy()[sel]))
    d = np.concatenate(diffs)
    den = np.concatenate(denoms)
    assert d.size > 25000, f"only {d.size} comparable bars"
    assert np.percentile(d, 99.8) < 1e-10, (
        f"BETA drifted on well-conditioned bars: p99.8={np.percentile(d, 99.8)}")
    bad = d > 1e-8
    assert bad.mean() < 0.005, (
        f"{100*bad.mean():.3f}% of bars disagree by more than 1e-8; the "
        f"measurement found 0.158%")
    assert np.median(den[bad]) < 1e-10 < np.median(den[~bad]), (
        f"the disagreeing bars are no longer the ill-conditioned ones: "
        f"median denominator bad={np.median(den[bad])}, "
        f"good={np.median(den[~bad])}")


# --------------------------------------------------------------------------
# The two things that were nearly got wrong
# --------------------------------------------------------------------------

def test_the_two_warmups_are_the_measured_ones():
    """37, not 12, for the lookback-63 read-outs -- shown by running both.

    This is the regression guard for the most expensive lesson in the port.
    Note the asymmetry it demonstrates: at warm-up 12 `HT_DCPERIOD` is EXACT
    and `HT_TRENDLINE` is not, so no single warm-up serves the whole family and
    a port that checked only `HT_DCPERIOD` would have shipped.
    """
    talib = _talib()
    df = _one("A1CAP_IS_1d.parquet")
    x = df["close"].astype(float).to_numpy()

    right = ht_state(x, _WARMUP_63)
    wrong = ht_state(x, _WARMUP_32)

    d_right, n = _maxdiff(right["trendline"], talib.HT_TRENDLINE(x), LOOKBACK_63)
    d_wrong, _ = _maxdiff(wrong["trendline"], talib.HT_TRENDLINE(x), LOOKBACK_63)
    assert n > 600
    assert d_right == 0.0, f"the 37-bar warm-up no longer reproduces talib: {d_right}"
    assert d_wrong > 0.1, (
        f"the 12-bar warm-up now also reproduces HT_TRENDLINE ({d_wrong}); "
        f"either talib changed or this test has gone blind")

    d_right, _ = _maxdiff(right["dcphase"], talib.HT_DCPHASE(x), LOOKBACK_63)
    d_wrong, _ = _maxdiff(wrong["dcphase"], talib.HT_DCPHASE(x), LOOKBACK_63)
    assert d_right < 1e-8 < 10.0 < d_wrong, (
        f"HT_DCPHASE: right={d_right}, wrong={d_wrong}")

    # ... and the other direction: at warm-up 12, HT_DCPERIOD is exact.
    d, _ = _maxdiff(ht_state(x, _WARMUP_32)["dcperiod"], talib.HT_DCPERIOD(x),
                    LOOKBACK_32)
    assert d < 1e-10, d


def test_the_hilbert_summation_order_is_load_bearing():
    """Reordering an algebraically identical sum changes MAMA by 1.1e-2.

    The mutant is the "obvious tidy-up": collect the four taps into one
    expression. It is a legal algebraic rewrite and a numerical one, and the
    clamped alpha turns the difference into a factor of ten on a frame with
    long runs of identical prices.
    """
    talib = _talib()
    df = _one("PETKM_IS_1d.parquet")
    x = df["close"].astype(float).to_numpy()
    mm, _fm = talib.MAMA(x)

    real, n = _maxdiff(ht_state(x, _WARMUP_32)["mama"], mm, LOOKBACK_32)
    assert n > 6000
    assert real < 1e-9, f"the shipped order stopped reproducing talib: {real}"

    spec = importlib.util.find_spec("pandas_ta.cycles._hilbert")
    source = open(spec.origin, encoding="utf8").read()
    mutated = source.replace(
        """    v = -(_A * arr[t - 6])
    v += _A * arr[t]
    v -= _B * arr[t - 4]
    v += _B * arr[t - 2]
    v *= adj
    return v""",
        """    return (_A * arr[t] + _B * arr[t - 2] - _B * arr[t - 4]
            - _A * arr[t - 6]) * adj""")
    assert mutated != source, "the mutation did not apply -- the test is blind"
    ns = {}
    exec(compile(mutated, "<mutant>", "exec"), ns)
    mut, _ = _maxdiff(ns["ht_state"](x, _WARMUP_32)["mama"], mm, LOOKBACK_32)
    assert mut > 1e-3, (
        f"the reordered mutant now agrees with talib to {mut}; either the "
        f"conditioning changed or this test has gone blind")


# --------------------------------------------------------------------------
# Gate B -- causality
# --------------------------------------------------------------------------

def test_state_machine_is_causal_under_future_perturbation():
    """Perturb every bar from J on; nothing before J may move.

    Prefix truncation cannot certify a recursion -- it cannot see back-dating
    -- so this is the detector `tests/test_pinebi_1e_utilities.py` settled on.
    Every shipped column is checked, not only the cycle ones.
    """
    o, h, l, c = _synthetic()
    n = len(c)
    J = 400
    bump = 50.0 * (np.arange(n) >= J)

    def build(o_, h_, l_, c_):
        parts = [
            ht_dcperiod(c_).to_frame(), ht_dcphase(c_).to_frame(),
            ht_phasor(c_), ht_sine(c_), ht_trendmode(c_).to_frame(),
            ht_trendline(c_), mama(c_), sarext(h_, l_, c_),
            imi(o_, c_).to_frame(), beta(c_, other=h_).to_frame(),
        ]
        import pandas as pd
        return pd.concat(parts, axis=1)

    base = build(o, h, l, c)
    shifted = build(o + bump, h + bump, l + bump, c + bump)
    assert list(base.columns) == list(shifted.columns)

    for col in base.columns:
        a, b = base[col].iloc[:J], shifted[col].iloc[:J]
        mask = ~(a.isna() | b.isna())
        assert int(mask.sum()) > 200, f"{col}: nothing settled to compare"
        leak = float((a[mask] - b[mask]).abs().max())
        assert leak == 0.0, f"{col} reads the future: leak={leak}"


def test_backdating_mutant_is_caught():
    """The detector above must actually catch a back-dated write.

    Without this, `leak == 0.0` above only proves the test is asleep.
    """
    import pandas as pd
    o, h, l, c = _synthetic()
    n = len(c)
    J = 400
    bump = 50.0 * (np.arange(n) >= J)

    spec = importlib.util.find_spec("pandas_ta.cycles._hilbert")
    source = open(spec.origin, encoding="utf8").read()
    mutated = source.replace(
        '        out["dcperiod"][t] = smooth_period',
        '        out["dcperiod"][max(t - 25, 0)] = smooth_period')
    assert mutated != source, "the mutation did not apply -- the test is blind"
    ns = {}
    exec(compile(mutated, "<mutant>", "exec"), ns)

    def dcperiod(series):
        st = ns["ht_state"](series.to_numpy(dtype=float), _WARMUP_32)
        return pd.Series(ns["blank_lookback"](st["dcperiod"], LOOKBACK_32),
                         index=series.index)

    a = dcperiod(c).iloc[:J]
    b = dcperiod(c + bump).iloc[:J]
    mask = ~(a.isna() | b.isna())
    leak = float((a[mask] - b[mask]).abs().max())
    assert leak > 0.0, (
        "the back-dated mutant was NOT caught, so the causality test above "
        "cannot certify anything")


# --------------------------------------------------------------------------
# Gate C -- reachability
# --------------------------------------------------------------------------

def test_every_shipped_column_fires_on_real_data():
    """All 8 surviving columns, on 20 real daily frames, with counts.

    "Fires" means finite AND not constant across the frame. `HT_TRENDMODE` is
    binary, so for it the assertion is that BOTH states occur; a flag that is
    always 1 is a constant column dressed as a feature.
    """
    import pandas as pd
    counts = {c: 0 for c in SHIPPED_COLUMNS}
    both_states = {"HT_TRENDMODE": set()}
    frames = 0
    for _name, df in _frames():
        o = df["open"].astype(float)
        h = df["high"].astype(float)
        l = df["low"].astype(float)
        c = df["close"].astype(float)
        out = pd.concat([
            ht_dcperiod(c).to_frame(), ht_dcphase(c).to_frame(),
            ht_phasor(c), ht_sine(c), ht_trendmode(c).to_frame(),
            imi(o, c).to_frame(),
        ], axis=1)
        frames += 1
        for col in SHIPPED_COLUMNS:
            assert col in out.columns, f"{col} not emitted"
            s = out[col].dropna()
            counts[col] += int(s.size)
            if col in both_states:
                both_states[col] |= set(np.unique(s.to_numpy()))
            else:
                assert s.size == 0 or s.nunique() > 1, (
                    f"{col} is constant on a real frame")
    assert frames >= 15, f"only {frames} frames"
    for col, n in counts.items():
        assert n > 10000, f"{col} fired on only {n} bars across {frames} frames"
    for col, seen in both_states.items():
        assert len(seen) >= 2, f"{col} only ever took the values {seen}"


# --------------------------------------------------------------------------
# Gate D -- scale invariance
# --------------------------------------------------------------------------

def _all_columns(o, h, l, c):
    """Every column a DEFAULT call emits, plus `beta`. Scale-free ones only.

    `ht_trendline`, `mama` and `sarext` are excluded: since the Gate E
    reverts they return TA-Lib's raw price LEVELS, which must NOT be
    scale-free. The dyadic test asserts exactly that about them separately, so
    the exclusion is checked rather than assumed.
    """
    import pandas as pd
    return pd.concat([
        ht_dcperiod(c).to_frame(), ht_dcphase(c).to_frame(),
        ht_phasor(c), ht_sine(c), ht_trendmode(c).to_frame(),
        imi(o, c).to_frame(), beta(c, other=h).to_frame(),
    ], axis=1)


@pytest.mark.parametrize("factor", [8.0, 64.0])
def test_dyadic_scale_invariance(factor):
    """Bit-identical under a power of two -- every shipped column.

    Powers of two are exact in binary floating point, so a column that is
    genuinely a ratio, an angle or a count must come back with the SAME BITS.
    This is the assertion that would fail if someone shipped a raw price level
    by accident: `HT_TRENDLINE`, `MAMA`, `FAMA` and `SAREXT` all fail it, which
    is why they are behind `raw=True`.
    """
    o, h, l, c = _synthetic()
    base = _all_columns(o, h, l, c)
    scaled = _all_columns(o * factor, h * factor, l * factor, c * factor)
    for col in base.columns:
        a, b = base[col], scaled[col]
        assert a.isna().equals(b.isna()), f"{col}: NaN masks differ at x{factor}"
        m = ~a.isna()
        assert int(m.sum()) > 300, f"{col}: nothing settled"
        assert (a[m].to_numpy() == b[m].to_numpy()).all(), (
            f"{col} is NOT scale-free at x{factor}: "
            f"max|diff|={float((a[m]-b[m]).abs().max())}")

    # and the price levels are NOT scale-free -- measured, so the claim that
    # they are levels is falsifiable rather than decorative
    for name, base_s, scaled_s in [
        ("MAMA_0.5_0.05", mama(c)["MAMA_0.5_0.05"],
         mama(c * factor)["MAMA_0.5_0.05"]),
        ("FAMA_0.5_0.05", mama(c)["FAMA_0.5_0.05"],
         mama(c * factor)["FAMA_0.5_0.05"]),
        ("HT_TRENDLINE", ht_trendline(c)["HT_TRENDLINE"],
         ht_trendline(c * factor)["HT_TRENDLINE"]),
        ("SAREXT_0.02_0.2",
         sarext(h, l, c)["SAREXT_0.02_0.2"],
         sarext(h * factor, l * factor, c * factor)["SAREXT_0.02_0.2"]),
    ]:
        m = ~base_s.isna()
        assert (base_s[m].to_numpy() != scaled_s[m].to_numpy()).any(), (
            f"{name} is scale-INVARIANT, which would mean it is no longer a "
            f"price level and the Gate D reasoning behind its exclusion from "
            f"`Category` is wrong")


def test_non_dyadic_scale_invariance():
    """x10 and x3.7 to tolerance, with matching NaN masks."""
    o, h, l, c = _synthetic()
    base = _all_columns(o, h, l, c)
    for factor in (10.0, 3.7):
        scaled = _all_columns(o * factor, h * factor, l * factor, c * factor)
        for col in base.columns:
            a, b = base[col], scaled[col]
            assert a.isna().equals(b.isna()), (
                f"{col}: NaN masks differ at x{factor}")
            m = ~a.isna()
            d = float((a[m] - b[m]).abs().max())
            scale = max(1.0, float(a[m].abs().max()))
            assert d <= 1e-8 * scale, f"{col} drifts at x{factor}: {d}"


# --------------------------------------------------------------------------
# Wiring and the optional dependency
# --------------------------------------------------------------------------

def test_the_shipped_six_are_registered_and_reachable():
    """Category, accessor and column names -- the three that drift apart.

    `tests/test_wiring_accessors.py` guards the general rule; this asserts the
    specific six, so a silent removal from `Category` fails HERE with the name
    that went missing.
    """
    from pandas_ta.core import AnalysisIndicators
    for category, names in REGISTERED.items():
        registered = pandas_ta.Category[category]
        for n in names:
            assert n in registered, f"{n} missing from Category['{category}']"
            assert hasattr(AnalysisIndicators, n), f"df.ta.{n} missing"


def test_the_four_unswept_ports_are_reachable_but_excluded():
    """`beta`, `ht_trendline`, `mama`, `sarext` -- callable, never swept.

    Absent from `Category` AND present in `strategy`'s exclusion list. Only
    the first was not enough earlier in this batch: `strategy("all")`
    enumerates ACCESSORS, so a function excluded from `Category` alone still
    ran and took the multiprocessing pool down with a `ValueError`.

    The reasons differ and both are worth keeping straight: `beta` needs a
    BENCHMARK series a single-frame sweep cannot supply, while `ht_trendline`,
    `mama` and `sarext` emit PRICE LEVELS because every one of their
    scale-free companions failed Gate E.
    """
    from pandas_ta.core import AnalysisIndicators
    flat = [n for v in pandas_ta.Category.values() for n in v]
    src = open(os.path.join(_FORK, "pandas_ta", "core.py"), encoding="utf8").read()
    body = src.split("excluded = [", 1)[1].split("]", 1)[0]
    for name in UNSWEPT:
        assert name not in flat, f"{name} must not be swept"
        assert hasattr(AnalysisIndicators, name), f"df.ta.{name} should exist"
        assert f'"{name}"' in body, (
            f"{name} is not in strategy()'s default exclusion list, so "
            f"strategy('all') will still run it")


def test_the_reverted_columns_stay_deleted():
    """The five Gate E casualties must not come back on a DEFAULT call.

    Deleting a column that measured at rho >= 0.90 is the expected outcome of
    Gate E, and the only thing that makes the deletion durable is a test that
    fails when someone "restores" it. Each is still reachable behind
    `emit_dist=True` for re-measurement, and that is asserted too -- a guard
    that also broke the re-measurement path would be worse than no guard.
    """
    _o, h, l, c = _synthetic(n=300)
    defaults = {
        "ht_trendline": ht_trendline(c),
        "mama": mama(c),
        "sarext": sarext(h, l, c),
    }
    for fname, frame_ in defaults.items():
        for col in frame_.columns:
            assert col not in REVERTED_COLUMNS, (
                f"{fname} emits {col} by default; it was DELETED on Gate E "
                f"({REVERTED_COLUMNS[col]}) and must not reach the miner")

    back = {
        **{c_: True for c_ in ht_trendline(c, emit_dist=True).columns},
        **{c_: True for c_ in mama(c, emit_dist=True).columns},
        **{c_: True for c_ in sarext(h, l, c, emit_dist=True).columns},
    }
    missing = [c_ for c_ in REVERTED_COLUMNS if c_ not in back]
    assert missing == [], (
        f"emit_dist no longer brings back {missing}, so the Gate E "
        f"measurement can no longer be reproduced")


def test_beta_refuses_to_invent_a_benchmark():
    _o, h, _l, c = _synthetic(n=120)
    with pytest.raises(ValueError):
        beta(c)


def test_no_shipped_module_imports_talib():
    """The fork's only consumer pip-installs it WITHOUT TA-Lib.

    Grep first, because it names the offending file. Then actually import the
    package with `talib` blocked and run every port, because a lazy import
    inside a function would slip past the grep.
    """
    # Two UPSTREAM modules import talib behind `if Imports["talib"]`, as an
    # optional acceleration path: `candles/cdl_pattern.py` and `momentum/dm.py`.
    # They predate this fork and are not TALIB-1's. The set is pinned so that a
    # THIRD one -- a TALIB-1 port quietly reaching for the oracle -- fails here.
    known = {os.path.join("pandas_ta", "candles", "cdl_pattern.py"),
             os.path.join("pandas_ta", "momentum", "dm.py")}
    offenders = set()
    for root, _dirs, files in os.walk(os.path.join(_FORK, "pandas_ta")):
        for f in files:
            if not f.endswith(".py"):
                continue
            p = os.path.join(root, f)
            text = open(p, encoding="utf8").read()
            for line in text.splitlines():
                s = line.strip()
                if s.startswith("import talib") or s.startswith("from talib"):
                    offenders.add(os.path.relpath(p, _FORK))
    assert offenders == known, (
        f"the set of modules importing talib changed: new={sorted(offenders-known)}, "
        f"gone={sorted(known-offenders)}")

    script = r"""
import sys
class Block:
    def find_module(self, name, path=None):
        if name == "talib" or name.startswith("talib."):
            return self
    def load_module(self, name):
        raise ImportError("talib blocked")
sys.meta_path.insert(0, Block())
sys.path.insert(0, %r)
import numpy as np, pandas as pd, pandas_ta as ta
n = 400
rng = np.random.default_rng(1)
c = pd.Series(100 + np.cumsum(rng.normal(0, 1, n)))
h = c + 1.0; l = c - 1.0; o = c + 0.1
from pandas_ta.cycles import ht_dcperiod, ht_dcphase, ht_phasor, ht_sine, ht_trendmode
from pandas_ta.momentum import imi
from pandas_ta.overlap import ht_trendline, mama
from pandas_ta.statistics import beta
from pandas_ta.trend import sarext
for r in (ht_dcperiod(c), ht_dcphase(c), ht_phasor(c), ht_sine(c),
          ht_trendmode(c), ht_trendline(c), mama(c), sarext(h, l, c),
          imi(o, c), beta(c, other=h)):
    assert r is not None
assert "talib" not in sys.modules
print("OK")
""" % _FORK
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True,
                          text=True, cwd=_FORK)
    assert proc.returncode == 0 and "OK" in proc.stdout, (
        f"the ports do not run without talib:\n{proc.stdout}\n{proc.stderr}")


def test_lookback_bars_are_withheld_exactly_as_talib_withholds_them():
    """The fork must not publish a bar TA-Lib itself declines to publish.

    32 for the lookback-32 family, 63 for the lookback-63 family. Measured as
    the index of the first finite value, on a frame long enough that neither
    is confused with "not enough data".
    """
    _o, _h, _l, c = _synthetic(n=400)
    first = {
        "HT_DCPERIOD": (ht_dcperiod(c), LOOKBACK_32),
        "HT_DCPHASE": (ht_dcphase(c), LOOKBACK_63),
        "HT_TRENDMODE": (ht_trendmode(c), LOOKBACK_63),
    }
    for name, (s, lb) in first.items():
        idx = int(np.argmax(s.notna().to_numpy()))
        assert idx == lb, f"{name} first fires at {idx}, TA-Lib's lookback is {lb}"
    for frame_, cols, lb in [(ht_phasor(c), ["HT_PHASOR_IP", "HT_PHASOR_Q"], LOOKBACK_32),
                             (ht_sine(c), ["HT_SINE", "HT_LEADSINE"], LOOKBACK_63),
                             (ht_trendline(c), ["HT_TRENDLINE"], LOOKBACK_63)]:
        for col in cols:
            idx = int(np.argmax(frame_[col].notna().to_numpy()))
            assert idx == lb, f"{col} first fires at {idx}, expected {lb}"
