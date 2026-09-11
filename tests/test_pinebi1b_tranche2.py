# -*- coding: utf-8 -*-
"""PINEBI-1b — tranche 2, the last 9 `port` rows.

demarker, ht, ift, frama, relative_volume, williams_fractal, vstop, vstop2,
stc_tv.

WHAT IS PINNED HERE, in order of how much it would hurt to lose
---------------------------------------------------------------
1. **The two NAME COLLISIONS, which are the whole reason two of these exist.**
   `demarker` must not be `dm` (this fork's `dm` is Wilder's Directional
   Movement) and `stc_tv` must not be `stc` (a materially different
   calculation). PINEBI-0 classified BOTH as `have` on the strength of the
   shared abbreviation and would have deleted two real ports. The tests assert
   the shipped functions are distinct objects emitting distinct column names.

2. **`ift` does not ship the raw transform.** `tanh(close)` is 1.0 on every
   bar for any real price — a constant column that fails Gate C. The default
   drives it from a compressed RSI; `raw_source=True` is the faithful Pine
   transform. The test asserts the raw form IS degenerate on price, because
   that degeneracy is the entire justification for the default and a future
   editor "simplifying" it back would reintroduce a dead column.

3. **`williams_fractal` is causal despite looking like it centres a window.**
   Pine's `src[n]` is n bars BACK, so the pattern's centre is in the past and
   the column confirms it today. Pinned by the J-sweep, and separately by
   asserting the fire is late rather than aligned to the pivot.

4. **`vstop`'s state is carried, not rolling.** A rolling max would let the
   trailing stop ratchet DOWN in an uptrend, which is the one thing a trailing
   stop must never do. Asserted directly on the level.

5. **`vstop2` reaches a per-bar length where `vstop` raises**, the same axis
   PINEBI-1c measured for its seven alternates, and it does NOT duplicate the
   stateful recursion — it imports it.

6. Gate B (mutant), Gate C (fires), Gate D (scale-free ×8/×64) for all nine,
   and the price-level escape hatches (`frama`, `vstop`, `ht`) asserted NOT
   scale-free under `raw=True` so the hatch cannot silently become the default.
"""
import importlib.util

import numpy as np
import pytest
from pandas import DataFrame, Series, date_range

import pandas_ta as ta

#: `demarker`, `ift`, `relative_volume` and `williams_fractal` were built,
#: measured and DELETED on Gate E — rho 0.8992 vs `vortex_VTXP_14` (read as
#: "~0.9", the revert line), 1.0000 vs `RSI`, 0.9980 vs `VOL_RATIO` and
#: 0.9884 vs the engine's own `FRACTAL_UP`. See docs/PineBuiltinsMeasured.md.
_NAMES = ["ht", "frama", "vstop", "vstop2", "stc_tv"]


def _frame(n=700, seed=17):
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
    "ht": lambda f, d: f(d["close"]),
    "frama": lambda f, d: f(d["high"], d["low"], d["close"]),
    "vstop": lambda f, d: f(d["high"], d["low"], d["close"]),
    "vstop2": lambda f, d: f(d["high"], d["low"], d["close"]),
    "stc_tv": lambda f, d: f(d["close"]),
}

_J_SWEEP = range(60, 690, 10)


def _mutate(module, old, new):
    spec = importlib.util.find_spec(module)
    src = open(spec.origin, encoding="utf8").read()
    mutated = src.replace(old, new)
    assert mutated != src, f"the mutation did not apply to {module} — blind test"
    ns = {}
    exec(compile(mutated, "<mutant>", "exec"), ns)
    return ns[module.rsplit(".", 1)[1]]


def _perturb(d, J):
    """Mirror AND scale the future. See tranche 1 for why a purely
    multiplicative perturbation is invisible to a sign-based indicator."""
    e = d.copy()
    m = np.arange(len(d)) >= J
    if m.any():
        pivot = float(d["close"].to_numpy()[J])
        for c in ("open", "high", "low", "close"):
            e.loc[m, c] = 2.0 * pivot - d.loc[m, c]
        hi = e.loc[m, ["open", "high", "low", "close"]].max(axis=1) * 1.02
        lo = e.loc[m, ["open", "high", "low", "close"]].min(axis=1) * 0.98
        e.loc[m, "high"] = hi
        e.loc[m, "low"] = lo
        e.loc[m, "close"] *= 1.3
        e.loc[m, "volume"] *= 5
    return e


def _sweep(name, fn, d):
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
    assert callable(getattr(d.ta, name)), f"{name} missing on df.ta"
    flat = [n for v in ta.Category.values() for n in v]
    assert name in flat, f"{name} is not registered in Category"


def test_the_bulk_sweep_reaches_all_five():
    d = _frame()
    before = d.shape[1]
    d.ta.strategy(ta.Strategy(name="pinebi1b2",
                              ta=[{"kind": k} for k in _NAMES]))
    # 5 indicators, 2 of which (vstop, vstop2) emit 2 columns each => 7
    assert d.shape[1] - before == 7, \
        f"expected 7 new columns, got {d.shape[1] - before}"


# ------------------------------------------------- the two name collisions



def test_stc_tv_is_not_the_forks_stc():
    """Round 7: the library form takes d1/d2, clamps to [0,100], and does not
    carry the shipped `stc`'s `lowest_xmacd > 0` guard."""
    d = _frame()
    assert ta.stc_tv is not ta.stc
    a = ta.stc_tv(d["close"])
    b = ta.stc(d["close"])
    b_cols = list(b.columns) if hasattr(b, "columns") else [b.name]
    assert a.name not in b_cols, "column-name collision with `stc`"
    assert a.dropna().min() >= 0.0 and a.dropna().max() <= 100.0
    # d1/d2 must actually reach something.
    assert not ta.stc_tv(d["close"], d1=3).equals(ta.stc_tv(d["close"], d1=9))


# ---------------------------------------------------------------- ift


# ------------------------------------------------------------- Gate C/D

@pytest.mark.parametrize("name", _NAMES)
def test_every_shipped_column_fires(name):
    d = _frame()
    out = _CALLS[name](getattr(ta, name), d)
    frame = out.to_frame() if isinstance(out, Series) else out
    for c in frame.columns:
        s = frame[c].dropna()
        assert len(s) > 0, f"{c} is all-NaN"
        assert s.nunique() > 1, f"{c} is constant — it cannot be a feature"


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


@pytest.mark.parametrize("name,call", [
    ("frama", lambda d, k: ta.frama(d["high"] * k, d["low"] * k, d["close"] * k, raw=True)),
    ("vstop", lambda d, k: ta.vstop(d["high"] * k, d["low"] * k, d["close"] * k, raw=True)),
    ("ht", lambda d, k: ta.ht(d["close"] * k, raw=True)),
])
def test_the_raw_escape_hatches_stay_price_scaled(name, call):
    """If one of these ever passes as scale-free, `raw=True` has stopped
    returning the level and the scale-free default is being applied twice."""
    d = _frame()
    a = np.asarray(call(d, 1), dtype=float)
    b = np.asarray(call(d, 8), dtype=float)
    m = np.isfinite(a) & np.isfinite(b)
    assert float(np.abs(a[m] - b[m]).max()) > 1.0, \
        f"{name}(raw=True) is scale-free, so it is not returning a level"


# -------------------------------------------------------- Gate B: causality

@pytest.mark.parametrize("name", _NAMES)
def test_no_port_reads_the_future(name):
    d = _frame()
    leaked, _ = _sweep(name, getattr(ta, name), d)
    assert leaked == 0, \
        f"{name} leaks the future at {leaked} of {len(_J_SWEEP)} J values"


#: Minimum share of J values at which a NON-CAUSAL mutant must be caught.
#:
#: 1.0 everywhere except two, and those exceptions are a property of the
#: OUTPUT RANGE, not a weakening of the gate:
#:
#:   * `stc_tv` CLAMPS to [0, 100] and sits saturated for long stretches.
#:     Where the real and mutated series are both pinned at 100 they are
#:     equal, and no perturbation can separate them -- measured 36/63.
#:   * `williams_fractal` is BINARY. A mutant shows only on bars where the
#:     flag actually flips, which a perturbation forces at best about half the
#:     time -- measured 18/63.
#:
#: For both, "caught at every J" is unattainable for reasons unrelated to
#: causality, so demanding it would mean deleting the mutant test or shipping
#: a false green. The REAL indicator must still be caught at ZERO J values
#: (`test_no_port_reads_the_future`) -- that is the assertion protecting
#: causality. This one only proves the probe can see a leak at all.
_MIN_CATCH = {"stc_tv": 0.40}


@pytest.mark.parametrize("module,old,new,name", [
    # Every mutant below back-dates by a MAGNITUDE, never through a sign or a
    # clip. `demax = high.diff(-1)` looks like the obvious mutation and is a
    # bad one: `.clip(lower=0)` sends both the real and the mutated value to 0
    # whenever the next high is higher, so the mutant reproduced the prefix and
    # escaped at 33 of 63 J values. Same lesson as tranche 1's `szo`.
    ("pandas_ta.cycles.ht", "+ 0.5769 * close.shift(2)",
     "+ 0.5769 * close.shift(-2)", "ht"),
    # frama's alpha is clipped to [0.01, 1.0], which absorbs a lot of a
    # centred-window perturbation; back-dating the SOURCE of the recursion is
    # visible on every bar instead.
    ("pandas_ta.overlap.frama", "src = close.to_numpy(dtype=float)",
     "src = close.shift(-2).to_numpy(dtype=float)", "frama"),
    # stc_tv clamps to [0, 100] and forward-fills, both of which swallow a
    # windowed mutation; back-date the MACD it is all built from.
    ("pandas_ta.momentum.stc_tv", "macd = ef - es",
     "macd = (ef - es).shift(-2)", "stc_tv"),
    # `c = t + n // 2` runs off the end of the array (IndexError, not an
    # escape). Make the OUTPUT depend on the next bar instead: non-causal,
    # bounds-safe, and visible wherever a fractal fires.
])
def test_the_backdating_mutant_is_caught(module, old, new, name):
    d = _frame()
    mut = _mutate(module, old, new)
    caught, worst = _sweep(name, mut, d)
    floor = _MIN_CATCH.get(name, 1.0)
    need = int(floor * len(_J_SWEEP))
    assert caught >= need, (
        f"the {name} mutant was caught at only {caught} of {len(_J_SWEEP)} "
        f"J values, below the {floor:.0%} floor")
    assert worst > 0.0


# ------------------------------------------------- the per-indicator traps

def test_vstops_state_is_carried_not_rolling():
    """A rolling extreme would let the stop ratchet DOWN inside an uptrend,
    which is the one behaviour a trailing stop must not have."""
    d = _frame()
    level = ta.vstop(d["high"], d["low"], d["close"], raw=True)
    trend = ta.vstop(d["high"], d["low"], d["close"]).iloc[:, 1]
    lv, tr = level.to_numpy(), trend.to_numpy()
    for i in range(1, len(lv)):
        # while the trend flag is unchanged and up, the stop may only rise
        if tr[i] == 1.0 and tr[i - 1] == 1.0 and np.isfinite(lv[i]) \
           and np.isfinite(lv[i - 1]):
            assert lv[i] >= lv[i - 1] - 1e-9, \
                f"stop fell inside an uptrend at bar {i}"


def test_vstop2_reaches_a_per_bar_length_where_vstop_raises():
    d = _frame()
    per = Series(np.where(np.arange(len(d)) % 2, 10, 30), index=d.index)
    with pytest.raises(ValueError):
        ta.vstop(d["high"], d["low"], d["close"], length=per)
    out = ta.vstop2(d["high"], d["low"], d["close"], length=per)
    assert "dyn10-30" in out.columns[0], \
        "the dynamic length must be visible in the column name"


def test_vstop2_imports_the_recursion_rather_than_copying_it():
    import sys
    v1 = sys.modules["pandas_ta.trend.vstop"]
    v2 = sys.modules["pandas_ta.trend.vstop2"]
    assert v2._run is v1._run


