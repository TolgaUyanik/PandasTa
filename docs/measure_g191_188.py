# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191188Measured.md for
`pandas_ta.volatility.g191_188`. Synthetic frames only (Gate E, the
real-data measurement, is run by the launcher after this session)."""
import importlib
import importlib.util
import types
from pathlib import Path

import numpy as np
import pandas as pd
from pandas import Series

from pandas_ta.volatility.g191_188 import g191_188
from pandas_ta.volatility.g191_109 import g191_109
from pandas_ta.volatility.atr import atr
from pandas_ta.volatility.cvi import cvi
from pandas_ta.volatility.g191_158 import g191_158
from pandas_ta.volatility.massi import massi
from pandas_ta.volatility.natr import natr
from pandas_ta.volatility.true_range import true_range

_REAL = importlib.import_module("pandas_ta.volatility.g191_188")

SCREEN = Path(__file__).resolve().parent / "issues" / "screen" / "ind_screen.py"

SMOOTH_LENGTH, SMOOTH_WEIGHT = 11, 2


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = close * rng2.uniform(0.005, 0.02, n)
    high = close + spread * rng2.uniform(0.3, 1.0, n)
    low = close - spread * rng2.uniform(0.3, 1.0, n)
    return (Series(high), Series(low), Series(close))


def _walk_clustered(n=1500, seed=11, sigma=0.015, rho=0.95, vol_of_vol=0.35):
    """The same lognormal close path, but with the bar SPREAD following an
    AR(1) in logs instead of being drawn i.i.d. -- i.e. with volatility
    clustering, which `_walk` has none of. Used only to test whether this
    column's overlap with `g191_158` (`(H-L)/close`) is a construction
    artefact of the i.i.d. frame: when the spread is a fixed fraction of
    close times an i.i.d. draw, `EMA(H-L)` is nearly proportional to close,
    so `(H-L)/close` and `(H-L)/EMA(H-L)` become monotone transforms of the
    same draw."""
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    shocks = np.random.default_rng(seed + 2).normal(0.0, vol_of_vol, n)
    log_vol = np.zeros(n)
    for i in range(1, n):
        log_vol[i] = rho * log_vol[i - 1] + shocks[i]
    spread = close * 0.01 * np.exp(log_vol)
    return (Series(close + 0.5 * spread), Series(close - 0.5 * spread),
            Series(close))


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_188_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _gtja_sma_local(series):
    """`SMA(series, 11, 2)` the way the port spells it, for side measurements
    that need the denominator itself rather than the column."""
    return series.ewm(alpha=SMOOTH_WEIGHT / SMOOTH_LENGTH, adjust=False,
                      min_periods=SMOOTH_LENGTH).mean()


def _prototype(high, low):
    """The issue's prototype (`docs/issues/screen/ind_screen.py:560-563`),
    RETYPED, because `docs/issues/` is gitignored and a clone does not carry
    it:

        e = sma(h - l, 11, 2)
        return 100 * sdiv(h - l - e, e)

    with `sma`/`sdiv` as `ind_screen.py:57-59`/`41-42` define them -- and
    note the prototype's `sma` carries NO `min_periods`, so this is the
    SOURCE spelling of the smoother, not the fork's."""
    r = high - low
    e = r.ewm(alpha=SMOOTH_WEIGHT / SMOOTH_LENGTH, adjust=False).mean()
    return 100 * ((r - e) / e).replace([np.inf, -np.inf], np.nan)


def _prototype_fork_sma(high, low):
    """The same prototype expression with the fork's `min_periods=n` on the
    GTJA `SMA` -- what the shipped module computes, spelled independently."""
    r = high - low
    e = r.ewm(alpha=SMOOTH_WEIGHT / SMOOTH_LENGTH, adjust=False,
              min_periods=SMOOTH_LENGTH).mean()
    return 100 * ((r - e) / e).replace([np.inf, -np.inf], np.nan)


def _rejected_precedence(high, low):
    """The reading the port REJECTS: `*100` scaling the DENOMINATOR, i.e.
    `(H-L-e) / (e*100)` instead of `((H-L-e)/e) * 100`."""
    r = high - low
    e = r.ewm(alpha=SMOOTH_WEIGHT / SMOOTH_LENGTH, adjust=False,
              min_periods=SMOOTH_LENGTH).mean()
    return ((r - e) / (e * 100)).replace([np.inf, -np.inf], np.nan)


def _real_candidate(high, low, close):
    """The REAL `g191_188` candidate out of the owner's screen module, when
    that (gitignored) file is present in this worktree."""
    spec = importlib.util.spec_from_file_location("_ind_screen", SCREEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ones = Series(np.ones(len(close)), index=close.index)
    return mod.REG["g191_188"]["fn"](close, high, low, close, ones)


def _independent_loop(high, low, t):
    """`G191_188[t]` from plain Python scalars: no `.ewm()`, no `.replace()`.
    The GTJA recursion is seeded exactly the way `adjust=False` seeds it --
    `Y` at the first valid input IS that input -- then run forward bar by
    bar."""
    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    y = None
    seen = 0
    for i in range(t + 1):
        ri = h[i] - l[i]
        if ri != ri:
            continue
        alpha = SMOOTH_WEIGHT / SMOOTH_LENGTH
        y = ri if y is None else alpha * ri + (1 - alpha) * y
        seen += 1
    if seen < SMOOTH_LENGTH:
        return float("nan")
    rt = h[t] - l[t]
    return 100 * ((rt - y) / y)


def main():
    high, low, close = _walk()
    out = g191_188(high, low)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")
    d = out.dropna()
    print(f"positive={int((d > 0).sum())} negative={int((d < 0).sum())} "
          f"zero={int((d == 0).sum())}")
    print(f"min-above-minus-100={bool((d > -100.0).all())}")

    # Gate D: price rescales.
    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_188(high * k, low * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        signs = int(((out[m] > 0) != (scaled[m] > 0)).sum())
        print(f"x{k} price max|diff|={max_diff!r} nan-mask-match={mask_match} "
              f"sign-changes={signs}")

    # Gate A: the shipped module vs the retyped prototype, the prototype's
    # OWN (no-min_periods) smoother, and the real screen candidate.
    pf = _prototype_fork_sma(high, low)
    pm = out.notna() & pf.notna()
    print("port vs retyped prototype (fork min_periods): over "
          f"{int(pm.sum())} shared bars "
          f"max|diff|={float((out[pm] - pf[pm]).abs().max())!r} "
          f"bit-equal bars={int((out[pm] == pf[pm]).sum())} of {int(pm.sum())}")
    pp = _prototype(high, low)
    qm = out.notna() & pp.notna()
    print(f"prototype's own sma (no min_periods) fires {int(pp.notna().sum())} "
          f"vs the port's {fires}; over {int(qm.sum())} shared bars "
          f"max|diff|={float((out[qm] - pp[qm]).abs().max())!r} "
          f"bit-equal bars={int((out[qm] == pp[qm]).sum())} of {int(qm.sum())}")

    if SCREEN.exists():
        cand = _real_candidate(high, low, close)
        cm = out.notna() & cand.notna()
        print("port vs REAL screen candidate: candidate non-NaN "
              f"{int(cand.notna().sum())} of {n}; over {int(cm.sum())} shared "
              f"bars max|diff|={float((out[cm] - cand[cm]).abs().max())!r} "
              f"bit-equal bars={int((out[cm] == cand[cm]).sum())}")
    else:
        print(f"port vs REAL screen candidate: SKIPPED, {SCREEN} absent")

    # Gate A: the rejected `*100` precedence reading.
    rej = _rejected_precedence(high, low)
    rm = out.notna() & rej.notna()
    ratio = (out[rm] / rej[rm])
    print("rejected precedence reading: shared bars "
          f"{int(rm.sum())} max|diff|={float((out[rm] - rej[rm]).abs().max())!r} "
          f"bit-equal bars={int((out[rm] == rej[rm]).sum())} "
          f"ratio min={float(ratio.min())!r} max={float(ratio.max())!r} "
          f"spearman={float(out[rm].corr(rej[rm], method='spearman'))!r} "
          f"sign-changes={int(((out[rm] > 0) != (rej[rm] > 0)).sum())}")

    # Gate A: an 8-bar hand example at smooth_length=3, smooth_weight=1.
    hand_high = Series([12.0, 14.0, 11.0, 18.0, 10.0, 22.0, 9.0, 26.0])
    hand_low = Series([8.0, 10.0, 8.0, 12.0, 6.0, 15.0, 5.0, 18.0])
    hand_out = g191_188(hand_high, hand_low, smooth_length=3, smooth_weight=1)
    print("hand-derived bars 0..7:", list(hand_out.iloc[0:8]))
    hr = hand_high - hand_low
    print("r (H-L):", list(hr))
    print("e (unmasked ewm alpha=1/3):",
          list(hr.ewm(alpha=1 / 3, adjust=False).mean()))
    print("e (masked, min_periods=3):",
          list(hr.ewm(alpha=1 / 3, adjust=False, min_periods=3).mean()))

    # Gate A: independent per-bar replay at the shipped defaults.
    big_high, big_low, _ = _walk(900, seed=3)
    out_defaults = g191_188(big_high, big_low)
    for t in (300, 600, 899):
        loop = _independent_loop(big_high, big_low, t)
        diff = abs(float(out_defaults.iloc[t]) - loop)
        print(f"independent-loop bar {t}: module={out_defaults.iloc[t]!r} "
              f"loop={loop!r} diff={diff:.3e}")

    # Gate B: future-perturbation leak counts, real module vs three mutants.
    other_h, other_l, _ = _walk(1500, seed=97)
    offsets = range(50, 1500, 40)

    def leaks(fn):
        base = fn(high, low)
        hits = 0
        for j in offsets:
            ph, pl = high.copy(), low.copy()
            ph.iloc[j:] = other_h.iloc[j:].values
            pl.iloc[j:] = other_l.iloc[j:].values
            o = fn(ph, pl)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(g191_188)} of {total}")
    write_shift = _load_mutant(
        "    result = 100 * ((r - e) / e).replace([np.inf, -np.inf], np.nan)",
        "    result = (100 * ((r - e) / e).replace([np.inf, -np.inf], np.nan)).shift(-smooth_length)",
    )
    print(f"write-shift mutant (smooth_length-bar look-ahead) leaks: "
          f"{leaks(write_shift.g191_188)} of {total}")
    lookahead_range = _load_mutant(
        "    r = high - low",
        "    r = high.shift(-1) - low.shift(-1)",
    )
    print(f"look-ahead-range mutant leaks: "
          f"{leaks(lookahead_range.g191_188)} of {total}")
    lookahead_ema = _load_mutant(
        "    e = _gtja_sma(r, smooth_length, smooth_weight)",
        "    e = _gtja_sma(r, smooth_length, smooth_weight).shift(-1)",
    )
    print(f"look-ahead-ema mutant leaks: "
          f"{leaks(lookahead_ema.g191_188)} of {total}")

    # Reachability / neighbours on the same synthetic frame. NOT Gate E.
    # `Range_ATR` is the engine column the issue's prototype hit at 0.8846.
    # This fork has no such column, but the CONSTRUCTION is reachable: a
    # range-like numerator over a smoothing of itself. Below: the shipped
    # neighbours, then the nearest proxy for the engine column, then six
    # variants off this port's own spelling. Four of them move ONE thing
    # (the smoother; the length at this port's own weight m=2, long and
    # short; or the numerator); `MEAN(range, 14)` and
    # `ewm(range, alpha=1/14)` are TWO-variable controls -- the latter is
    # `SMA(14,1)`, a Wilder RMA, so it moves both `n` and `m` and roughly
    # triples the smoother's centre of mass (4.5 bars at alpha 2/11, 13 at
    # alpha 1/14).
    r_here = high - low
    tr_here = true_range(high, low, close)
    tr_bigger = int((tr_here > r_here).sum())
    tr_shared = int((tr_here.notna() & r_here.notna()).sum())
    neighbours = {
        "g191_109:G191_109_10_2_10_2": g191_109(high, low),
        "massi:MASSI_9_25": massi(high, low),
        "cvi:CVI_10_10": cvi(high, low),
        "g191_158:G191_158": g191_158(high, low, close),
        "natr:NATR_14": natr(high, low, close),
        "true_range:TRUERANGE_1": tr_here,
        "Range_ATR proxy: true_range / Wilder RMA(true_range, 14)":
            tr_here / atr(high, low, close, 14),
        "vary the SMOOTHER only: range / MEAN(range, 11)":
            r_here / r_here.rolling(SMOOTH_LENGTH).mean(),
        "vary the LENGTH only: range / ewm(range, alpha=2/14) = SMA(14,2)":
            r_here / r_here.ewm(alpha=SMOOTH_WEIGHT / 14, adjust=False,
                                min_periods=14).mean(),
        "vary the LENGTH only, short: range / ewm(range, alpha=2/5) = SMA(5,2)":
            r_here / r_here.ewm(alpha=SMOOTH_WEIGHT / 5, adjust=False,
                                min_periods=5).mean(),
        "vary LENGTH and WEIGHT: range / ewm(range, alpha=1/14) = SMA(14,1)":
            r_here / r_here.ewm(alpha=1 / 14, adjust=False,
                                min_periods=14).mean(),
        "vary LENGTH and SMOOTHER: range / MEAN(range, 14)":
            r_here / r_here.rolling(14).mean(),
        "vary the NUMERATOR only: true_range / ewm(true_range, alpha=2/11)":
            tr_here / tr_here.ewm(alpha=SMOOTH_WEIGHT / SMOOTH_LENGTH,
                                  adjust=False,
                                  min_periods=SMOOTH_LENGTH).mean(),
    }
    print("-- synthetic neighbour overlap (NOT Gate E) --")
    print(f"true_range > high - low on {tr_bigger} of {tr_shared} bars "
          f"({100 * tr_bigger / tr_shared:.2f}%), so the Range_ATR proxy "
          f"substitutes its numerator too")
    for label, series in neighbours.items():
        mm = out.notna() & series.notna()
        rho = float(out[mm].corr(series[mm], method="spearman"))
        print(f"{label}: spearman={rho:.6f} shared={int(mm.sum())}")

    # Is the g191_158 overlap a construction artefact of the i.i.d. frame?
    # On `_walk`, H-L = close * (an i.i.d. draw), so EMA(H-L) is nearly
    # proportional to close. Measure that proportionality, then re-measure
    # the overlap on a frame WITH volatility clustering.
    e_here = _gtja_sma_local(r_here)
    ratio_ec = (e_here / close).dropna()
    print(f"e/close on the i.i.d. walk: mean={float(ratio_ec.mean()):.6f} "
          f"std={float(ratio_ec.std()):.6f} "
          f"cv={float(ratio_ec.std() / ratio_ec.mean()):.6f}")
    ch, cl, cc = _walk_clustered()
    c_out = g191_188(ch, cl)
    c_e = _gtja_sma_local(ch - cl)
    c_ratio = (c_e / cc).dropna()
    print(f"e/close on the clustered walk: mean={float(c_ratio.mean()):.6f} "
          f"std={float(c_ratio.std()):.6f} "
          f"cv={float(c_ratio.std() / c_ratio.mean()):.6f}")
    for label, series in (("g191_158:G191_158", g191_158(ch, cl, cc)),
                          ("g191_109:G191_109_10_2_10_2", g191_109(ch, cl)),
                          ("range / MEAN(range, 11)",
                           (ch - cl) / (ch - cl).rolling(SMOOTH_LENGTH).mean())):
        mm = c_out.notna() & series.notna()
        rho = float(c_out[mm].corr(series[mm], method="spearman"))
        print(f"clustered walk vs {label}: spearman={rho:.6f} "
              f"shared={int(mm.sum())}")

    # Edge cases: a dead-bar stretch and a NaN in the input.
    zh = high.copy()
    zl = low.copy()
    zl.iloc[:] = zh.iloc[:]          # every bar H == L
    zero_out = g191_188(zh, zl)
    print(f"all-dead-bars frame: fires={int(zero_out.notna().sum())} of {n} "
          f"(0/0 is NaN directly, no inf to replace)")
    dh, dl = high.copy(), low.copy()
    dl.iloc[700] = dh.iloc[700]      # one dead bar inside a normal frame
    dead_out = g191_188(dh, dl)
    print(f"one dead bar at 700: value={float(dead_out.iloc[700])!r} "
          f"fires={int(dead_out.notna().sum())}")
    nh = high.copy()
    nh.iloc[700] = np.nan
    nan_out = g191_188(nh, low)
    both = out.notna() & nan_out.notna()
    mv = out.index[both & (out != nan_out)]
    newly_nan = int((out.notna() & nan_out.isna()).sum())
    print(f"one NaN in high at 700: fires={int(nan_out.notna().sum())} "
          f"newly-NaN={newly_nan} displaced={len(mv)} "
          f"first_displaced={int(mv[0])} last_displaced={int(mv[-1])} "
          f"first_valid={int(nan_out.notna().idxmax())}")
    print(f"pandas={pd.__version__} numpy={np.__version__}")


if __name__ == "__main__":
    main()
