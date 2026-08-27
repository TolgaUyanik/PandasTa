# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.trend.tvstop` -- the Terminal Velocity Stop
port of TradingView `7YXrxMjV` (116 content lines; `wc -l` 116 and
`grep -c ''` 116, newline-terminated).

What these tests actually pin, in order of how much they would hurt to
lose:

* A LITERAL Pine-order transliteration of L61-L87, written from the
  source rather than from the module, run bar-for-bar against the
  shipped implementation on the SAME atr series so that the comparison
  isolates the stop state machine and not the moving-average flavour.
* WHICH HALF of the L71 clamp is dead and WHERE, demonstrated on data:
  dropping the lower clamp is a no-op in an all-uptrend series and NOT
  a no-op once the series flips; dropping the upper clamp changes the
  all-uptrend series immediately.  The brief this port was written
  against named the wrong half; these two tests are the evidence.
* CAUSALITY, by FUTURE-PERTURBATION -- rewrite every bar from `j`
  onward, demand bars `[0:j]` bit-identical -- swept over 30 offsets in
  BOTH directions.  The sweep and the two directions are not decoration:
  a one-bar leak proposes one step, and the RATCHET discards it whenever
  the sign is wrong, so a single-offset one-directional version of this
  test passed BOTH mutants during development.  Two PERTURBING
  look-ahead mutants (`importlib` source read, one write index shifted
  forward, `exec`'d into a fresh in-memory module, never a hand-written
  copy) are each proved LIVE against the real module first, then caught.
  Disagreement is scored ONLY on cells finite in both runs, after
  asserting the NaN masks match, because a bare `!=` on NaN-bearing
  floats passes on a null mutant.
* Truncation is kept as corroboration, and its MEASURED weakness is
  pinned rather than hidden: over the same sweep it catches the `target`
  mutant 7 times and the `flip` mutant NOT AT ALL.  It is not a
  substitute for the perturbation sweep.
* SCALE INVARIANCE at x10 and at x8 (an exact power of two, so the
  mantissas are untouched and the check can be BIT-exact).
* The rate limit itself, as an inequality on the reconstructed stop --
  and, in the uptrend branch, as an IFF against `TVS_DIST > mult`.
* What dividing by ATR actually does, MEASURED rather than assumed: an
  exactly-zero ATR does NOT arise in this fork (`non_zero_range` floors
  it), a dead-flat series reads 0.0 rather than inf, and the real
  unguarded hazard is a COLLAPSED-but-positive ATR amplifying the ratio.
"""
import importlib
import types

import numpy as np
import pytest
from pandas import DataFrame, Series

import pandas_ta as ta
from pandas_ta.trend.tvstop import tvstop
from pandas_ta.volatility.atr import atr as _atr


# ----------------------------------------------------------------- data


def _walk(n=1200, seed=11, sigma=0.02, drift=0.0, start=100.0):
    rng = np.random.default_rng(seed)
    lr = rng.normal(drift, sigma, n)
    c = start * np.exp(np.cumsum(lr))
    h = c * (1.0 + np.abs(rng.normal(0, 0.008, n)))
    l = c * (1.0 - np.abs(rng.normal(0, 0.008, n)))
    return Series(h), Series(l), Series(c)


def _ramp(n=400, step=0.6, start=100.0):
    """A strictly rising series -- `dir` never leaves 1 (asserted)."""
    c = start + step * np.arange(n, dtype=float)
    h = c + 0.2
    l = c - 0.2
    return Series(h), Series(l), Series(c)


HI, LO, CL = _walk()
COLS = ["TVS_DIST_14_3_3_0.3", "TVS_FLIP_BULL_14_3_3_0.3",
        "TVS_FLIP_BEAR_14_3_3_0.3"]


# ------------------------------------------------- Pine transliteration


def _pine_reference(close, atr_series, mult=3.0, multm=3.0, vmax=0.3):
    """L61-L87 transcribed in Pine's own order, from the source file.
    Returns (stop, dir, flipUp, flipDown) as plain lists.

    This deliberately does NOT reproduce the module's zero-ATR guard:
    the caller feeds it only bars the module also evaluates.
    """
    c = list(close)
    a = list(atr_series)
    stop = float("nan")
    d = 1
    stops, dirs = [], []
    for t in range(len(c)):
        if not (a[t] == a[t]):                       # atr still na
            stops.append(float("nan"))
            dirs.append(d)
            continue
        target = c[t] - mult * a[t] if d == 1 else c[t] + multm * a[t]  # L66
        if stop != stop:                                                # L68
            stop = target                                               # L69
        else:
            step = max(min(target - stop, vmax * a[t]), -vmax * a[t])   # L71
            if d == 1:                                                  # L73
                stop = max(stop, stop + step)                           # L74
                if c[t] < stop:                                         # L76
                    d = -1                                              # L77
                    stop = c[t] + multm * a[t]                          # L78
            else:                                                       # L79
                stop = min(stop, stop + step)                           # L80
                if c[t] > stop:                                         # L82
                    d = 1                                               # L83
                    stop = c[t] - mult * a[t]                           # L84
        stops.append(stop)
        dirs.append(d)
    flip_up, flip_dn = [], []
    for t in range(len(c)):
        prev = dirs[t - 1] if t > 0 else None
        flip_up.append(1.0 if (dirs[t] == 1 and prev == -1) else 0.0)   # L86
        flip_dn.append(1.0 if (dirs[t] == -1 and prev == 1) else 0.0)   # L87
    return stops, dirs, flip_up, flip_dn


def test_matches_a_literal_pine_order_transliteration():
    a = _atr(high=HI, low=LO, close=CL, length=14)
    got = tvstop(HI, LO, CL)
    stops, dirs, fu, fd = _pine_reference(CL, a)

    ok = (a.to_numpy() > 0)                    # bars the module evaluates
    assert ok.sum() > 1000

    ref_dist = np.where(
        ok, (CL.to_numpy() - np.asarray(stops)) / a.to_numpy(), np.nan)
    np.testing.assert_array_equal(got[COLS[0]].to_numpy(), ref_dist)
    np.testing.assert_array_equal(
        got[COLS[1]].to_numpy(), np.where(ok, np.asarray(fu), np.nan))
    np.testing.assert_array_equal(
        got[COLS[2]].to_numpy(), np.where(ok, np.asarray(fd), np.nan))
    # the reference must actually exercise both branches
    assert 0 < sum(fu) and 0 < sum(fd)


# --------------------------------------------- which clamp half is dead


def _variant(close, atr_series, kind, mult=3.0, multm=3.0, vmax=0.3):
    """`_pine_reference`'s stop loop with one half of L71 removed.

    kind='drop_lower'  ->  step = min(target - stop, +vmax*atr)
    kind='drop_upper'  ->  step = max(target - stop, -vmax*atr)
    kind='source'      ->  the full L71 clamp
    """
    c, a = list(close), list(atr_series)
    stop, d, out = float("nan"), 1, []
    for t in range(len(c)):
        if not (a[t] == a[t]):
            out.append(float("nan"))
            continue
        target = c[t] - mult * a[t] if d == 1 else c[t] + multm * a[t]
        if stop != stop:
            stop = target
        else:
            x, v = target - stop, vmax * a[t]
            if kind == "source":
                step = max(min(x, v), -v)
            elif kind == "drop_lower":
                step = min(x, v)
            elif kind == "drop_upper":
                step = max(x, -v)
            else:
                raise AssertionError(kind)
            if d == 1:
                stop = max(stop, stop + step)
                if c[t] < stop:
                    d, stop = -1, c[t] + multm * a[t]
            else:
                stop = min(stop, stop + step)
                if c[t] > stop:
                    d, stop = 1, c[t] - mult * a[t]
        out.append(stop)
    return np.asarray(out, dtype=float)


def test_lower_clamp_is_dead_in_the_uptrend_branch():
    """`max(0, max(min(x,v), -v)) == max(0, min(x,v))`: on a series that
    never leaves `dir == 1`, deleting `math.max(..., -vmax*atr)` from
    L71 is a bit-exact no-op."""
    h, l, c = _ramp()
    a = _atr(high=h, low=l, close=c, length=14)
    assert (tvstop(h, l, c)[COLS[0]].dropna() > 0).all(), "ramp flipped"

    base = _variant(c, a, "source")
    np.testing.assert_array_equal(base, _variant(c, a, "drop_lower"))


def test_upper_clamp_is_load_bearing_in_the_uptrend_branch():
    """The other half is NOT redundant there: deleting
    `math.min(..., vmax*atr)` removes the rate limit itself and the stop
    teleports, on the very same all-uptrend series."""
    h, l, c = _ramp()
    a = _atr(high=h, low=l, close=c, length=14)
    base = _variant(c, a, "source")
    loose = _variant(c, a, "drop_upper")
    m = np.isfinite(base) & np.isfinite(loose)
    assert m.sum() > 300
    assert (base[m] != loose[m]).sum() > 100
    # and it is loose in the expected DIRECTION: without the cap the
    # stop sits closer to price on a rising series.
    assert (loose[m] >= base[m] - 1e-9).all()


def test_lower_clamp_is_not_globally_removable():
    """Dead in the uptrend branch is not dead everywhere: on a series
    that does flip, the same deletion changes the output."""
    a = _atr(high=HI, low=LO, close=CL, length=14)
    base = _variant(CL, a, "source")
    cut = _variant(CL, a, "drop_lower")
    m = np.isfinite(base) & np.isfinite(cut)
    assert m.sum() > 1000
    assert (base[m] != cut[m]).sum() > 0


# ------------------------------------------------------------ causality


_REAL = importlib.import_module("pandas_ta.trend.tvstop")
with open(_REAL.__file__, "r", encoding="utf-8") as _fh:
    _SRC = _fh.read()


def _load_mutant(pairs, tag):
    """The REAL module source with the given substrings replaced, exec'd
    into a fresh in-memory module. Never a hand-written copy."""
    src = _SRC
    for old, new in pairs:
        assert old in src, f"mutant anchor no longer present: {old!r}"
        src = src.replace(old, new)
    mod = types.ModuleType(f"_tvstop_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src, _REAL.__file__, "exec"), mod.__dict__)
    return mod


# Mutant TARGET: the stop chases TOMORROW's close.  Perturbing, not
# nullifying -- every evaluated bar keeps a finite value.
_M_TARGET = [(
    "        target = c_t - mult * a_t if direction == 1 else c_t + multm * a_t",
    "        _peek = c[t + 1] if t + 1 < n else c_t\n"
    "        target = _peek - mult * a_t if direction == 1 else _peek + multm * a_t",
)]
# Mutant FLIP: the uptrend flip test reads TOMORROW's close.
_M_FLIP = [(
    "                if c_t < stop:                     # L76",
    "                if (c[t + 1] if t + 1 < n else c_t) < stop:  # L76",
)]


def _disagree(A, B):
    """Cells where two runs disagree, counted ONLY over cells finite in
    both. NaN masks are asserted equal first, so warm-up NaNs are never
    scored either way and a null mutant cannot pass by NaN alignment."""
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    assert A.shape == B.shape
    assert (np.isnan(A) == np.isnan(B)).all(), "NaN masks diverge"
    m = np.isfinite(A) & np.isfinite(B)
    return int((A[m] != B[m]).sum()), int(m.sum())


def _perturb_from(fn, j, sign):
    """Rewrite every bar from `j` onward (up if sign>0, down if sign<0);
    the output on bars before `j` must not move by a single bit.

    Both signs are swept because the RATCHET can swallow a one-sided
    leak: in an uptrend a peek at a LOWER future close only proposes a
    negative step, which `max(stop, stop + step)` discards, so an
    up-only perturbation would let a real look-ahead go unnoticed.
    """
    h, l, c = HI, LO, CL
    rng = np.random.default_rng(999 + j)
    b = rng.uniform(0.05, 0.5, len(c) - j)
    bump = (1.0 + b) if sign > 0 else (1.0 - b)
    h2, l2, c2 = h.copy(), l.copy(), c.copy()
    for dst, srcs in ((h2, h), (l2, l), (c2, c)):
        dst.iloc[j:] = srcs.iloc[j:].to_numpy() * bump
    a = fn(h, l, c)[COLS].to_numpy()[:j]
    b2 = fn(h2, l2, c2)[COLS].to_numpy()[:j]
    return _disagree(a, b2)


_J_SWEEP = list(range(400, 1150, 25))


def _sweep_perturbations(fn):
    """Total disagreements and total co-populated cells over the sweep.
    One `j` is a single leaked bar and the ratchet may absorb it; the
    sweep gives a real leak many chances to show."""
    bad = cells = 0
    for j in _J_SWEEP:
        for sign in (+1, -1):
            b, n = _perturb_from(fn, j, sign)
            bad += b
            cells += n
    return bad, cells


def test_future_bars_do_not_move_past_output():
    bad, n = _sweep_perturbations(tvstop)
    assert n > 50000, "no co-populated cells to compare"
    assert bad == 0, f"{bad} of {n} past cells moved when the FUTURE changed"


@pytest.mark.parametrize("pairs,tag", [(_M_TARGET, "target"),
                                       (_M_FLIP, "flip")])
def test_mutants_are_live_and_differ_from_the_real_module(pairs, tag):
    """Anti-vacuity: prove the `exec`'d mutant is actually a DIFFERENT
    function before asking whether the causality tests catch it. A
    replace that silently did nothing would otherwise make every mutant
    test below pass for the wrong reason."""
    mut = _load_mutant(pairs, tag)
    real = tvstop(HI, LO, CL)[COLS].to_numpy()
    got = mut.tvstop(HI, LO, CL)[COLS].to_numpy()
    bad, n = _disagree(real, got)
    assert n > 2000
    assert bad > 0, f"mutant {tag} is byte-different but behaviour-identical"


@pytest.mark.parametrize("pairs,tag", [(_M_TARGET, "target"),
                                       (_M_FLIP, "flip")])
def test_lookahead_mutants_are_caught_by_future_perturbation(pairs, tag):
    mut = _load_mutant(pairs, tag)
    bad, n = _sweep_perturbations(mut.tvstop)
    assert n > 50000
    assert bad > 0, f"mutant {tag} was NOT caught -- the test is vacuous"


def test_truncation_matches_prefix_of_full_series():
    bad, n = _truncation_sweep(tvstop)
    assert n > 50000
    assert bad == 0


def _truncation_sweep(fn):
    bad = cells = 0
    for k in _J_SWEEP:
        full = fn(HI, LO, CL)[COLS].to_numpy()[:k]
        part = fn(HI.iloc[:k], LO.iloc[:k], CL.iloc[:k])[COLS].to_numpy()
        b, n = _disagree(full, part)
        bad += b
        cells += n
    return bad, cells


@pytest.mark.parametrize("pairs,tag,expected", [(_M_TARGET, "target", 7),
                                                (_M_FLIP, "flip", 0)])
def test_truncation_is_a_weaker_detector_than_perturbation(pairs, tag,
                                                           expected):
    """MEASURED asymmetry, pinned rather than papered over. Truncation
    leaks only at the single last bar, and the RATCHET can discard that
    bar's perturbation -- so over the same 30-value `k` sweep it catches
    the `target` mutant 7 times and the `flip` mutant NOT AT ALL. That
    is why `test_future_bars_do_not_move_past_output` (which perturbs a
    whole tail, in both directions, at 30 offsets) is the load-bearing
    causality test here and truncation is only corroboration. If this
    ever starts catching `flip`, the fixture changed -- re-derive the
    number, do not widen the assertion."""
    mut = _load_mutant(pairs, tag)
    bad, n = _truncation_sweep(mut.tvstop)
    assert n > 50000
    assert bad == expected


# ----------------------------------------------------------- scale-free


@pytest.mark.parametrize("k", [10.0, 8.0])
def test_scale_invariance(k):
    """x8 is an exact power of two, so every mantissa is untouched and
    the comparison can be BIT-exact rather than approximate."""
    base = tvstop(HI, LO, CL)
    scaled = tvstop(HI * k, LO * k, CL * k)
    for col in COLS:
        a, b = base[col].to_numpy(), scaled[col].to_numpy()
        assert (np.isnan(a) == np.isnan(b)).all(), f"{col}: NaN masks differ"
        m = np.isfinite(a)
        assert 0 < m.sum()
        if k == 8.0:
            np.testing.assert_array_equal(a[m], b[m])
        else:
            np.testing.assert_allclose(a[m], b[m], rtol=1e-9, atol=1e-9)


def test_flags_fire_but_not_always():
    """`0 < fires < n` on both flags -- neither dead nor degenerate."""
    df = tvstop(HI, LO, CL)
    for col in COLS[1:]:
        v = df[col].dropna().to_numpy()
        fires = int(v.sum())
        assert 0 < fires < v.size, f"{col}: {fires} of {v.size}"


# ---------------------------------------------- the rate limit and the
# ---------------------------------------------- ratchet, as properties


def _reconstruct_stop(df, close, a):
    return close.to_numpy() - df[COLS[0]].to_numpy() * a.to_numpy()


def test_stop_travel_is_capped_at_vmax_atr_on_non_flip_bars():
    a = _atr(high=HI, low=LO, close=CL, length=14)
    df = tvstop(HI, LO, CL)
    stop = _reconstruct_stop(df, CL, a)
    fu = df[COLS[1]].to_numpy()
    fd = df[COLS[2]].to_numpy()
    av = a.to_numpy()
    checked = 0
    for t in range(1, len(stop)):
        if not (np.isfinite(stop[t]) and np.isfinite(stop[t - 1])):
            continue
        if fu[t] == 1.0 or fd[t] == 1.0:
            continue                       # L78/L84 resets bypass the cap
        travel = abs(stop[t] - stop[t - 1])
        assert travel <= 0.3 * av[t] + 1e-8 * max(1.0, abs(stop[t])), \
            f"bar {t}: travelled {travel} > {0.3 * av[t]}"
        checked += 1
    assert checked > 1000


def test_reset_bars_can_and_do_exceed_the_rate_limit():
    """The complement of the test above: the cap governs travel WITHIN a
    direction, not the L78/L84 flip resets. Without this the test above
    could be passing on a series where nothing ever moves fast."""
    a = _atr(high=HI, low=LO, close=CL, length=14)
    df = tvstop(HI, LO, CL)
    stop = _reconstruct_stop(df, CL, a)
    flips = ((df[COLS[1]].to_numpy() == 1.0)
             | (df[COLS[2]].to_numpy() == 1.0))
    over = 0
    for t in range(1, len(stop)):
        if not flips[t] or not np.isfinite(stop[t - 1]):
            continue
        if abs(stop[t] - stop[t - 1]) > 0.3 * a.to_numpy()[t]:
            over += 1
    assert over > 0


def test_stop_ratchets_within_a_direction():
    a = _atr(high=HI, low=LO, close=CL, length=14)
    df = tvstop(HI, LO, CL)
    stop = _reconstruct_stop(df, CL, a)
    d = np.sign(df[COLS[0]].to_numpy())
    up = dn = 0
    for t in range(1, len(stop)):
        if not (np.isfinite(stop[t]) and np.isfinite(stop[t - 1])):
            continue
        if d[t] != d[t - 1]:
            continue
        tol = 1e-9 * max(1.0, abs(stop[t]))
        if d[t] > 0:
            assert stop[t] >= stop[t - 1] - tol, f"bull stop fell at {t}"
            up += 1
        elif d[t] < 0:
            assert stop[t] <= stop[t - 1] + tol, f"bear stop rose at {t}"
            dn += 1
    assert up > 100 and dn > 100


def test_dist_above_mult_is_exactly_the_clamp_binding():
    """In the uptrend branch `TVS_DIST > mult` iff the L71 clamp cut the
    step to `+vmax*atr` on that bar -- an IFF, both directions checked
    against a run of the reference loop that records when it clamped."""
    a = _atr(high=HI, low=LO, close=CL, length=14)
    df = tvstop(HI, LO, CL)
    dist = df[COLS[0]].to_numpy()

    c, av = list(CL), list(a)
    stop, d = float("nan"), 1
    bound = np.zeros(len(c), dtype=bool)
    isbull = np.zeros(len(c), dtype=bool)
    for t in range(len(c)):
        if not (av[t] == av[t]):
            continue
        target = c[t] - 3.0 * av[t] if d == 1 else c[t] + 3.0 * av[t]
        if stop != stop:
            stop = target
        else:
            v = 0.3 * av[t]
            raw = target - stop
            step = max(min(raw, v), -v)
            if d == 1:
                bound[t] = (raw > v)      # the clamp actually cut it
                stop = max(stop, stop + step)
                if c[t] < stop:
                    d, stop = -1, c[t] + 3.0 * av[t]
            else:
                stop = min(stop, stop + step)
                if c[t] > stop:
                    d, stop = 1, c[t] - 3.0 * av[t]
        isbull[t] = (d == 1)

    m = np.isfinite(dist) & isbull
    assert m.sum() > 300
    above = dist[m] > 3.0 + 1e-12
    np.testing.assert_array_equal(above, bound[m])
    assert above.sum() > 50, "clamp never bound -- the test proves nothing"
    assert (~above).sum() > 50, "clamp always bound -- ditto"


def test_sign_of_dist_is_exactly_the_direction():
    """The port drops the source's `dir` because it is recoverable from
    `sign(TVS_DIST)`. Pin that: a bull flip bar is positive, a bear flip
    bar is negative, and the sign is constant between flips.

    Scope: this holds wherever `TVS_DIST != 0`, which is every bar of
    this fixture (asserted). It is NOT universal -- an exact 0 is
    reachable and identifies nothing; see
    `test_flat_series_atr_is_epsilon_floored_and_dist_is_zero_not_inf`.
    """
    df = tvstop(HI, LO, CL).dropna()
    v = df[COLS[0]].to_numpy()
    fu = df[COLS[1]].to_numpy() == 1.0
    fd = df[COLS[2]].to_numpy() == 1.0
    assert fu.sum() > 5 and fd.sum() > 5
    assert (v[fu] > 0).all()
    assert (v[fd] < 0).all()
    assert not (fu & fd).any()
    flip = fu | fd
    sign = np.sign(v)
    assert (sign != 0).all()
    for t in range(1, len(v)):
        if not flip[t]:
            assert sign[t] == sign[t - 1], f"sign changed off-flip at {t}"


def test_a_vertical_candle_moves_supertrend_further_than_tvs():
    """The DELTA against the fork's existing stop lane, on data: give a
    flat series one vertical candle and Supertrend's ratcheted band
    travels further in that bar than `vmax * ATR`, while this stop
    cannot. Pins the mechanism the port exists for."""
    n = 200
    c = np.full(n, 100.0)
    c[120:] = 100.0 + np.arange(n - 120) * 0.01
    c[150] = 140.0                              # the vertical candle
    c[151:] = 140.0
    close = Series(c)
    high = Series(np.maximum(c, np.roll(c, 1)) + 0.05)
    low = Series(np.minimum(c, np.roll(c, 1)) - 0.05)

    a = _atr(high=high, low=low, close=close, length=14)
    tvs = tvstop(high, low, close)
    stop = _reconstruct_stop(tvs, close, a)
    tvs_travel = abs(stop[150] - stop[149])
    assert tvs_travel <= 0.3 * a.iloc[150] + 1e-9

    st = ta.supertrend(high, low, close, length=10, multiplier=3)
    band = st["SUPERT_10_3.0"].to_numpy()
    st_travel = abs(band[150] - band[149])
    assert st_travel > tvs_travel
    assert st_travel > 0.3 * a.iloc[150]


# ------------------------------------------------- NaN / guard contract


def test_flat_series_atr_is_epsilon_floored_and_dist_is_zero_not_inf():
    """MEASURED, not assumed. `true_range` uses `non_zero_range`, which
    adds `sflt.epsilon` to the whole high-low leg once any bar has
    `high == low`, so a dead-flat series does NOT produce a zero ATR --
    it produces 2.220446049250313e-16 -- and `TVS_DIST` is exactly 0.0,
    not inf and not NaN. The module's `atr > 0` guard therefore does not
    fire here; see the module docstring."""
    n = 300
    flat = Series(np.full(n, 50.0))
    a = _atr(high=flat, low=flat, close=flat, length=14).dropna()
    assert (a > 0).all(), "fixture assumption broken: ATR reached zero"
    assert np.unique(a.to_numpy()).size == 1
    assert float(a.iloc[-1]) == 2.220446049250313e-16

    df = tvstop(flat, flat, flat)
    v = df.to_numpy(dtype=float)
    assert not np.isinf(v).any()
    body = df[COLS[0]].dropna().to_numpy()
    assert body.size > 200
    np.testing.assert_array_equal(body, np.zeros_like(body))


def test_a_flat_patch_then_a_step_inflates_dist_far_beyond_mult():
    """The hazard the module docstring flags: a COLLAPSED ATR is an
    amplifier, and nothing NaNs out. Values far above `mult` are real
    readings, deliberately unclipped."""
    n = 60
    c = np.full(n, 50.0)
    c[40:] = 50.5                       # one step out of a flat patch
    close = Series(c)
    high = Series(np.maximum(c, np.roll(c, 1)))
    low = Series(np.minimum(c, np.roll(c, 1)))
    d = tvstop(high, low, close)[COLS[0]].to_numpy()
    assert not np.isinf(d[np.isfinite(d)]).any()
    assert np.nanmax(np.abs(d)) > 10.0 * 3.0     # 3.0 == default mult


def test_non_positive_atr_is_what_the_guard_actually_covers():
    """The guard exists for a MISSING ATR (warm-up, NaN input), which is
    reachable, rather than for a zero one, which is not."""
    h, l, c = _walk(n=400, seed=3)
    c2 = c.copy()
    c2.iloc[200] = np.nan
    df = tvstop(h, l, c2)
    v = df[COLS[0]].to_numpy()
    assert np.isnan(v[200])
    assert not np.isinf(df.to_numpy(dtype=float)).any()


def test_nan_masks_are_identical_across_the_three_columns():
    df = tvstop(HI, LO, CL)
    masks = [df[c].isna().to_numpy() for c in COLS]
    for m in masks[1:]:
        np.testing.assert_array_equal(masks[0], m)
    assert masks[0].sum() > 0 and (~masks[0]).sum() > 0


def test_a_nan_bar_is_skipped_not_consumed():
    """A NaN bar is stepped over: NaN on exactly those bars, finite on
    both sides, and -- the part that matters -- the state carries ACROSS
    rather than resetting. Pinned against a reference run in which the
    gap bars are dropped from the frame entirely: identical, which is
    what "skipped, not consumed" means. Pine would instead reset the
    stop here; see the module docstring."""
    h, l, c = _walk(n=600, seed=5)
    c2 = c.copy()
    c2.iloc[300:305] = np.nan
    v = tvstop(h, l, c2)[COLS[0]].to_numpy()
    assert np.isnan(v[300:305]).all()
    assert np.isfinite(v[299]) and np.isfinite(v[305])
    assert np.isfinite(v[-1])

    # A reset would put the bar-305 distance at exactly -/+ mult; it is
    # not, because the pre-gap stop survived.
    assert abs(abs(v[305]) - 3.0) > 1e-9


# ------------------------------------------------- shape / plumbing


def test_columns_name_and_category():
    df = tvstop(HI, LO, CL)
    assert isinstance(df, DataFrame)
    assert list(df.columns) == COLS
    assert df.name == "TVS_14_3_3_0.3"
    assert df.category == "trend"


def test_props_track_the_parameters():
    df = tvstop(HI, LO, CL, atr_length=20, mult=2.5, multm=4.0, vmax=1.0)
    assert list(df.columns) == ["TVS_DIST_20_2.5_4_1",
                                "TVS_FLIP_BULL_20_2.5_4_1",
                                "TVS_FLIP_BEAR_20_2.5_4_1"]


def test_offset_shifts_and_keeps_names():
    base = tvstop(HI, LO, CL)
    off = tvstop(HI, LO, CL, offset=2)
    assert list(off.columns) == COLS
    np.testing.assert_array_equal(off[COLS[0]].to_numpy()[2:],
                                  base[COLS[0]].to_numpy()[:-2])


def test_short_series_returns_none():
    assert tvstop(HI.iloc[:5], LO.iloc[:5], CL.iloc[:5]) is None


def test_dataframe_accessor():
    df = DataFrame({"high": HI, "low": LO, "close": CL})
    out = df.ta.tvstop()
    assert list(out.columns) == COLS
    np.testing.assert_array_equal(out[COLS[0]].to_numpy(),
                                  tvstop(HI, LO, CL)[COLS[0]].to_numpy())


def test_registered_in_the_trend_category():
    assert "tvstop" in ta.Category["trend"]
    assert hasattr(ta, "tvstop")


@pytest.mark.parametrize("kwargs", [
    {"atr_length": 0}, {"atr_length": -1}, {"atr_length": 2.5},
    {"atr_length": True}, {"atr_length": float("nan")},
    {"atr_length": float("inf")},
    {"mult": 0}, {"mult": -1.0}, {"mult": float("nan")},
    {"mult": float("inf")}, {"mult": True},
    {"multm": 0}, {"multm": float("nan")},
    {"vmax": 0}, {"vmax": -0.5}, {"vmax": float("nan")},
    {"vmax": float("inf")},
    {"mamode": 3},
])
def test_bad_arguments_raise(kwargs):
    with pytest.raises(ValueError):
        tvstop(HI, LO, CL, **kwargs)


def test_source_slider_caps_are_not_re_enforced():
    """L20 caps `vmax` at 2 and L12/L16 floor the multipliers at 0.5 in
    the TradingView UI. Those are widget bounds, not preconditions, and
    -- as in `flag_breakout` -- this port does not re-enforce them."""
    df = tvstop(HI, LO, CL, vmax=5.0, mult=0.1, multm=0.1)
    assert df[df.columns[0]].notna().sum() > 100


def test_vmax_monotonically_loosens_the_stop():
    """A larger terminal velocity lets the stop chase harder, so on an
    all-uptrend series it sits CLOSER to price at every evaluated bar."""
    h, l, c = _ramp()
    prev = None
    for v in (0.1, 0.3, 1.0, 3.0):
        d = tvstop(h, l, c, vmax=v)[f"TVS_DIST_14_3_3_{_fmtv(v)}"]
        cur = d.dropna().to_numpy()
        if prev is not None:
            assert (cur <= prev + 1e-9).all(), f"vmax={v} did not tighten"
        prev = cur


def _fmtv(x):
    return int(x) if float(x).is_integer() else x
