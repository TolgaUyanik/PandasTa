# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191110Measured.md for
`pandas_ta.momentum.g191_110`. Synthetic frames only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import importlib.util
import types
from pathlib import Path

import numpy as np
import pandas as pd
from pandas import Series

from pandas_ta.momentum.brar import brar
from pandas_ta.momentum.cmo import cmo
from pandas_ta.momentum.g191_110 import g191_110
from pandas_ta.momentum.g191_129 import g191_129
from pandas_ta.momentum.g191_167 import g191_167
from pandas_ta.momentum.imi import imi
from pandas_ta.momentum.psl import psl
from pandas_ta.momentum.rsi import rsi

_REAL = importlib.import_module("pandas_ta.momentum.g191_110")

SCREEN = Path(__file__).resolve().parent / "issues" / "screen" / "ind_screen.py"

LENGTH = 20


def _walk(n=1500, seed=11, sigma=0.015):
    """A lognormal close path with i.i.d. intrabar spreads. `high`/`low`
    bracket `close`, so every bar is OHLC-consistent, but NOT the prior
    close -- a gap bar whose whole range sits above `close[t-1]` is exactly
    what this column's denominator is made of."""
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = close * rng2.uniform(0.005, 0.02, n)
    high = close + spread * rng2.uniform(0.3, 1.0, n)
    low = close - spread * rng2.uniform(0.3, 1.0, n)
    open_ = low + (high - low) * rng2.uniform(0.0, 1.0, n)
    return (Series(high), Series(low), Series(close), Series(open_))


def _gap_up_frame(n=40):
    """Every bar's low sits ABOVE the prior close, so `MAX(0, C1-L)` is zero
    on every bar and the denominator's 20-bar sum is exactly 0. The
    numerator is 2.0 on every bar, so the division is `x/0` -> `+inf`, which
    the `.replace()` turns into NaN."""
    close = 100.0 + np.arange(n, dtype=float)
    return (Series(close + 1.0), Series(close - 0.5), Series(close))


def _frozen_frame(n=40):
    """H == L == C, constant: numerator AND denominator are both exactly 0,
    so the division is `0/0` -- NaN directly, with no `inf` to replace."""
    close = np.full(n, 100.0)
    return (Series(close.copy()), Series(close.copy()), Series(close.copy()))


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_110_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _prototype(high, low, close, length=LENGTH):
    """The issue's prototype (`docs/issues/screen/ind_screen.py:459-463`),
    RETYPED, because `docs/issues/` is gitignored and a clone does not carry
    it:

        c1 = delay(c, 1)
        return 100 * sdiv(tsum((h - c1).clip(lower=0), 20),
                          tsum((c1 - l).clip(lower=0), 20))

    with `delay`/`tsum`/`sdiv` as `ind_screen.py:45`/`49`/`41-42` define
    them. `tsum` is `rolling(n).sum()`, i.e. pandas' default
    `min_periods=n`, which the port spells out explicitly."""
    c1 = close.shift(1)
    num = (high - c1).clip(lower=0).rolling(length).sum()
    den = (c1 - low).clip(lower=0).rolling(length).sum()
    return 100 * (num / den).replace([np.inf, -np.inf], np.nan)


def _rejected_precedence(high, low, close, length=LENGTH):
    """The reading the port REJECTS: `*100` scaling the DENOMINATOR, i.e.
    `SUM(up) / (SUM(down) * 100)` instead of `(SUM(up)/SUM(down)) * 100`."""
    c1 = close.shift(1)
    num = (high - c1).clip(lower=0).rolling(length, min_periods=length).sum()
    den = (c1 - low).clip(lower=0).rolling(length, min_periods=length).sum()
    return (num / (den * 100)).replace([np.inf, -np.inf], np.nan)


def _tsmax_misreading(high, low, close, length=LENGTH):
    """The reading the port REJECTS on `MAX`: GTJA191's WINDOWED `TSMAX`
    instead of the pointwise two-argument max against the scalar 0. Under
    that reading `MAX(0, H-C1)` would be `TSMAX(H-C1, 0)`, which has no
    window at all, so the only coherent windowed form is
    `TSMAX(H-C1, length)` -- the window maximum rather than a per-bar
    floor."""
    c1 = close.shift(1)
    num = (high - c1).rolling(length, min_periods=length).max()
    den = (c1 - low).rolling(length, min_periods=length).max()
    return 100 * (num / den).replace([np.inf, -np.inf], np.nan)


def _scalar_on_the_numerator(high, low, close, length=LENGTH):
    """A THIRD parse of the `*100`, and the one the fork's own `brar` uses
    (`pandas_ta/momentum/brar.py:32-33`): multiply the NUMERATOR by 100 and
    then divide, `(100*SUM(up)) / SUM(down)`. Algebraically identical to the
    shipped `100 * (SUM(up)/SUM(down))`, but a DIFFERENT float64 rounding --
    which is why this is measured rather than waved through."""
    c1 = close.shift(1)
    num = (high - c1).clip(lower=0).rolling(length, min_periods=length).sum()
    den = (c1 - low).clip(lower=0).rolling(length, min_periods=length).sum()
    return ((100 * num) / den).replace([np.inf, -np.inf], np.nan)


def _where_instead_of_clip(high, low, close, length=LENGTH):
    """The spelling of `MAX(0, .)` this port REJECTS:
    `np.where(x > 0, x, 0.0)`, which maps a NaN input to `0.0` (a NaN fails
    the `> 0` test and falls down the else branch) instead of preserving it
    the way `Series.clip(lower=0)` does. At bar 0, where `C1` is undefined,
    that fabricates a `0.0` contribution out of a bar that has none."""
    c1 = close.shift(1)
    up = Series(np.where(high - c1 > 0, high - c1, 0.0), index=close.index)
    down = Series(np.where(c1 - low > 0, c1 - low, 0.0), index=close.index)
    num = up.rolling(length, min_periods=length).sum()
    den = down.rolling(length, min_periods=length).sum()
    return 100 * (num / den).replace([np.inf, -np.inf], np.nan)


def _monotone_twin(high, low, close, length=LENGTH):
    """`100 * up / (up + down)` -- the RSI/`BR`-to-`RSI` reparametrisation of
    the SAME two sums. `x/(x+y)` is a strictly increasing function of `x/y`
    on `x, y >= 0`, so it is a rank-identical restatement: anything mined on
    ranks cannot tell the two apart."""
    c1 = close.shift(1)
    num = (high - c1).clip(lower=0).rolling(length, min_periods=length).sum()
    den = (c1 - low).clip(lower=0).rolling(length, min_periods=length).sum()
    return 100 * (num / (num + den)).replace([np.inf, -np.inf], np.nan)


def _real_candidate(high, low, close):
    """The REAL `g191_110` candidate out of the owner's screen module, when
    that (gitignored) file is present in this worktree."""
    spec = importlib.util.spec_from_file_location("_ind_screen", SCREEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ones = Series(np.ones(len(close)), index=close.index)
    return mod.REG["g191_110"]["fn"](close, high, low, close, ones)


def _independent_loop(high, low, close, t, length=LENGTH):
    """`G191_110[t]` from plain Python scalars: no `.rolling()`, no
    `.clip()`, no `.replace()`. Walks the trailing window by hand."""
    h = high.to_numpy(dtype=float)
    lo = low.to_numpy(dtype=float)
    c = close.to_numpy(dtype=float)
    num = den = 0.0
    for i in range(t - length + 1, t + 1):
        if i < 1:
            return float("nan")
        up = h[i] - c[i - 1]
        dn = c[i - 1] - lo[i]
        num += up if up > 0.0 else 0.0
        den += dn if dn > 0.0 else 0.0
    if den == 0.0:
        return float("nan")
    return 100 * (num / den)


def main():
    high, low, close, open_ = _walk()
    out = g191_110(high, low, close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    d = out.dropna()
    print(f"min={float(d.min()):.6f} max={float(d.max()):.6f} "
          f"median={float(d.median()):.6f}")
    print(f"above-100={int((d > 100).sum())} below-100={int((d < 100).sum())} "
          f"exactly-100={int((d == 100).sum())} negative={int((d < 0).sum())} "
          f"zero={int((d == 0).sum())}")

    # Gate D: price rescales.
    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_110(high * k, low * k, close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        bit_equal = int((out[m] == scaled[m]).sum())
        print(f"x{k} price max|diff|={max_diff!r} nan-mask-match={mask_match} "
              f"bit-equal={bit_equal} of {int(m.sum())}")

    # Gate D: the two clip() branch masks under each rescale. The clip is an
    # exact comparison against 0, so a bar changing branch would be a real
    # scale dependence rather than rounding.
    c1 = close.shift(1)
    up_pos = (high - c1) > 0
    dn_pos = (c1 - low) > 0
    for k in (8.0, 64.0, 10.0, 3.7):
        k_up = (high * k - c1 * k) > 0
        k_dn = (c1 * k - low * k) > 0
        print(f"x{k} clip-branch changes: up={int((up_pos != k_up).sum())} "
              f"down={int((dn_pos != k_dn).sum())}")

    # Gate A: the shipped module vs the retyped prototype and the real
    # screen candidate.
    pf = _prototype(high, low, close)
    pm = out.notna() & pf.notna()
    print("port vs retyped prototype: shared bars "
          f"{int(pm.sum())} (port fires {fires}, prototype "
          f"{int(pf.notna().sum())}) "
          f"max|diff|={float((out[pm] - pf[pm]).abs().max())!r} "
          f"bit-equal bars={int((out[pm] == pf[pm]).sum())} of {int(pm.sum())}")
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
    rej = _rejected_precedence(high, low, close)
    rm = out.notna() & rej.notna()
    ratio = out[rm] / rej[rm]
    print("rejected precedence reading: shared bars "
          f"{int(rm.sum())} bit-equal bars={int((out[rm] == rej[rm]).sum())} "
          f"ratio min={float(ratio.min())!r} max={float(ratio.max())!r} "
          f"spearman={float(out[rm].corr(rej[rm], method='spearman'))!r}")

    # Gate A: the rejected windowed-TSMAX reading of `MAX(0, .)`.
    ts = _tsmax_misreading(high, low, close)
    tm = out.notna() & ts.notna()
    print("rejected TSMAX reading: shared bars "
          f"{int(tm.sum())} bit-equal bars={int((out[tm] == ts[tm]).sum())} "
          f"spearman={float(out[tm].corr(ts[tm], method='spearman')):.6f} "
          f"max|diff|={float((out[tm] - ts[tm]).abs().max()):.6f}")

    # Gate A: the third parse of `*100` (the fork's own `brar` spelling),
    # algebraically identical and NOT bit-identical.
    sn = _scalar_on_the_numerator(high, low, close)
    sm = out.notna() & sn.notna()
    print("scalar-on-the-numerator parse ((100*num)/den, brar's spelling): "
          f"shared bars {int(sm.sum())} "
          f"bit-equal bars={int((out[sm] == sn[sm]).sum())} of {int(sm.sum())} "
          f"max|diff|={float((out[sm] - sn[sm]).abs().max())!r} "
          f"spearman={float(out[sm].corr(sn[sm], method='spearman'))!r}")

    # Gate A: the rejected `np.where` spelling of `MAX(0, .)`, which turns
    # bar 0's undefined contribution into a fabricated 0.0.
    wh = _where_instead_of_clip(high, low, close)
    print("np.where spelling of MAX(0,.): fires="
          f"{int(wh.notna().sum())} vs the port's {fires}; "
          f"first_valid={int(wh.notna().idxmax())} vs {first_valid}; "
          f"bars where both fire and differ="
          f"{int(((out.notna() & wh.notna()) & (out != wh)).sum())}")

    # Gate A: an 8-bar hand example at length=3.
    hand_high = Series([11.0, 13.0, 10.0, 14.0, 13.0, 15.0, 12.0, 16.0])
    hand_low = Series([9.0, 10.0, 8.0, 11.0, 11.0, 12.0, 10.0, 13.0])
    hand_close = Series([10.0, 11.0, 9.0, 12.0, 12.0, 13.0, 11.0, 14.0])
    hand_out = g191_110(hand_high, hand_low, hand_close, length=3)
    hc1 = hand_close.shift(1)
    print("hand-derived up   (MAX(0,H-C1)):",
          list((hand_high - hc1).clip(lower=0)))
    print("hand-derived down (MAX(0,C1-L)):",
          list((hc1 - hand_low).clip(lower=0)))
    print("hand-derived bars 0..7:", list(hand_out.iloc[0:8]))

    # Gate A: independent per-bar replay at the shipped default length.
    bh, bl, bc, _ = _walk(900, seed=3)
    out_defaults = g191_110(bh, bl, bc)
    for t in (300, 600, 899):
        loop = _independent_loop(bh, bl, bc, t)
        diff = abs(float(out_defaults.iloc[t]) - loop)
        print(f"independent-loop bar {t}: module={out_defaults.iloc[t]!r} "
              f"loop={loop!r} diff={diff:.3e}")

    # Gate B: future-perturbation leak counts, real module vs three mutants.
    oh, ol, oc, _ = _walk(1500, seed=97)
    offsets = range(50, 1500, 40)

    def leaks(fn):
        base = fn(high, low, close)
        hits = 0
        for j in offsets:
            ph, pl, pc = high.copy(), low.copy(), close.copy()
            ph.iloc[j:] = oh.iloc[j:].values
            pl.iloc[j:] = ol.iloc[j:].values
            pc.iloc[j:] = oc.iloc[j:].values
            o = fn(ph, pl, pc)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(g191_110)} of {total}")
    write_shift = _load_mutant(
        "    result = 100 * (up_sum / down_sum).replace([np.inf, -np.inf], np.nan)",
        "    result = (100 * (up_sum / down_sum).replace([np.inf, -np.inf], np.nan)).shift(-length)",
    )
    print(f"write-shift mutant (length-bar look-ahead) leaks: "
          f"{leaks(write_shift.g191_110)} of {total}")
    forward_delay = _load_mutant(
        "    prev_close = close.shift(1)",
        "    prev_close = close.shift(-1)",
    )
    print(f"forward-DELAY mutant (C1 = tomorrow's close) leaks: "
          f"{leaks(forward_delay.g191_110)} of {total}")
    centered_sum = _load_mutant(
        "    up_sum = up.rolling(length, min_periods=length).sum()",
        "    up_sum = up.rolling(length, min_periods=length, center=True).sum()",
    )
    print(f"centered-numerator-sum mutant leaks: "
          f"{leaks(centered_sum.g191_110)} of {total}")
    centered_den = _load_mutant(
        "    down_sum = down.rolling(length, min_periods=length).sum()",
        "    down_sum = down.rolling(length, min_periods=length, center=True).sum()",
    )
    print(f"centered-denominator-sum mutant leaks: "
          f"{leaks(centered_den.g191_110)} of {total}")

    # ------------------------------------------------ non-redundancy
    # The headline: `brar`'s BR is THIS formula at length 26. Measure the
    # port against BR at the SAME length (is it the same column?) and
    # against the SHIPPED BR_26 (is it a restatement of a shipped column?).
    br20 = brar(open_, high, low, close, length=LENGTH)["BR_20"]
    bm = out.notna() & br20.notna()
    print("-- brar BR at the SAME length 20 --")
    print(f"shared={int(bm.sum())} (port fires {fires}, BR_20 "
          f"{int(br20.notna().sum())}) "
          f"max|diff|={float((out[bm] - br20[bm]).abs().max())!r} "
          f"bit-equal={int((out[bm] == br20[bm]).sum())} of {int(bm.sum())} "
          f"spearman={float(out[bm].corr(br20[bm], method='spearman'))!r}")
    # Is the 100-placement the WHOLE difference from `brar` on this frame?
    # `non_zero_range` only perturbs anything when some difference is
    # exactly 0, so check that first, then compare `brar` with the port's
    # own expression re-spelled brar's way.
    sn_here = _scalar_on_the_numerator(high, low, close)
    snm = sn_here.notna() & br20.notna()
    print("exact ties on this frame: H==C1 on "
          f"{int((high - c1).eq(0).sum())} bars, C1==L on "
          f"{int((c1 - low).eq(0).sum())} bars (non_zero_range's epsilon "
          "fires only when one of these is non-zero)")
    print("brar BR_20 vs the port's expression re-spelled brar's way "
          f"((100*num)/den): bit-equal={int((sn_here[snm] == br20[snm]).sum())} "
          f"of {int(snm.sum())} "
          f"max|diff|={float((sn_here[snm] - br20[snm]).abs().max())!r}")
    print(f"BR_20 non-finite: inf={int(np.isinf(br20).sum())} "
          f"nan={int(br20.isna().sum())}; port inf={int(np.isinf(out).sum())} "
          f"nan={int(out.isna().sum())}")

    # `non_zero_range` adds float_info.epsilon to the WHOLE difference series
    # whenever ANY element is exactly 0, which is the only thing separating
    # `brar`'s spelling from `MAX(0, .)`. Plant exact ties to reach it.
    th, tl, tc = high.copy(), low.copy(), close.copy()
    th.iloc[500] = tc.iloc[499]          # H == C1 exactly
    tl.iloc[600] = tc.iloc[599]          # L == C1 exactly
    t_out = g191_110(th, tl, tc)
    t_br = brar(open_, th, tl, tc, length=LENGTH)["BR_20"]
    tmm = t_out.notna() & t_br.notna()
    print("with exact H==C1 / L==C1 ties planted at 500 / 600: "
          f"shared={int(tmm.sum())} "
          f"max|diff|={float((t_out[tmm] - t_br[tmm]).abs().max())!r} "
          f"bit-equal={int((t_out[tmm] == t_br[tmm]).sum())} of {int(tmm.sum())}")

    # The differences from `brar` that are NOT the 100's placement, measured
    # rather than listed from memory. (1) the inf: already printed on the
    # gap-up frame below. (2) the history guard: `brar` calls
    # `verify_series(.., length)` and this port `verify_series(.., length+1)`.
    # (3) `brar.py:38` writes `br = ar.shift(offset)`, so at a non-zero
    # offset its BR column is the AR column shifted TWICE.
    n20 = LENGTH
    br_short = brar(open_.iloc[:n20], high.iloc[:n20], low.iloc[:n20],
                    close.iloc[:n20], length=LENGTH)
    port_short = g191_110(high.iloc[:n20], low.iloc[:n20], close.iloc[:n20])
    print(f"with exactly {n20} bars of history: port returns "
          f"{'None' if port_short is None else 'a Series'}; brar returns "
          f"{'None' if br_short is None else 'a DataFrame'} whose BR_20 is "
          f"non-NaN on "
          f"{'n/a' if br_short is None else int(br_short['BR_20'].notna().sum())} bars")
    br_off = brar(open_, high, low, close, length=LENGTH, offset=2)
    br_base = brar(open_, high, low, close, length=LENGTH)
    ar_twice = br_base["AR_20"].shift(4)
    om = br_off["BR_20"].notna() & ar_twice.notna()
    print("brar at offset=2: its BR_20 equals its own AR_20 shifted 4 on "
          f"{int((br_off['BR_20'][om] == ar_twice[om]).sum())} of "
          f"{int(om.sum())} shared bars (brar.py:38, `br = ar.shift(offset)`)")
    port_off = g191_110(high, low, close, offset=2)
    pm2 = port_off.notna()
    print("port at offset=2: equals the base shifted by 2 on "
          f"{int((port_off[pm2] == out.shift(2)[pm2]).sum())} of "
          f"{int(pm2.sum())} bars")

    print("-- synthetic neighbour overlap (NOT Gate E) --")
    neighbours = {
        "brar:BR_26 (THIS formula at length 26)":
            brar(open_, high, low, close)["BR_26"],
        "brar:AR_26 (the open-based sibling)":
            brar(open_, high, low, close)["AR_26"],
        "the monotone twin 100*up/(up+down), same two sums":
            _monotone_twin(high, low, close),
        "g191_167:G191_167_12 (SUM(MAX(C-C1,0),12)/C, the numerator's cousin)":
            g191_167(close),
        "g191_129:G191_129_12 (SUM(MAX(C1-C,0),12)/C, the denominator's cousin)":
            g191_129(close),
        "the two cousins' own ratio, 100*g191_167/g191_129":
            100 * (g191_167(close) / g191_129(close)).replace(
                [np.inf, -np.inf], np.nan),
        "rsi:RSI_14": rsi(close),
        "cmo:CMO_14": cmo(close),
        "psl:PSL_12": psl(close),
        "imi:IMI_14": imi(open_, close),
    }
    for label, series in neighbours.items():
        mm = out.notna() & series.notna()
        rho = float(out[mm].corr(series[mm], method="spearman"))
        # full precision too: the monotone twin's rho is quoted as "exactly
        # 1.0" in the receipt, and `:.6f` cannot support that word.
        print(f"{label}: spearman={rho:.6f} ({rho!r}) shared={int(mm.sum())}")

    # How much of the overlap with BR_26 is just "a 20-bar sum resembles a
    # 26-bar sum"? One variable at a time: the SAME formula at other lengths.
    print("-- same formula, other lengths (locates the 20) --")
    for k in (5, 10, 15, 19, 21, 26, 40, 60):
        other = g191_110(high, low, close, length=k)
        mm = out.notna() & other.notna()
        rho = float(out[mm].corr(other[mm], method="spearman"))
        print(f"length {k}: spearman={rho:.6f} shared={int(mm.sum())}")

    # ------------------------------------------------ edge cases
    gh, gl, gc = _gap_up_frame()
    g_out = g191_110(gh, gl, gc)
    gc1 = gc.shift(1)
    g_den = (gc1 - gl).clip(lower=0).rolling(LENGTH, min_periods=LENGTH).sum()
    g_num = (gh - gc1).clip(lower=0).rolling(LENGTH, min_periods=LENGTH).sum()
    g_raw = g_num / g_den
    print(f"all-gap-up frame (L > C1 on every bar): fires="
          f"{int(g_out.notna().sum())} of {len(g_out)}; raw ratio inf on "
          f"{int(np.isinf(g_raw).sum())} bars, nan on {int(g_raw.isna().sum())}")
    # One bar that trades back below its prior close rescues the windows
    # containing it.
    rh, rl, rc = _gap_up_frame()
    rl.iloc[30] = rc.iloc[29] - 1.0
    r_out = g191_110(rh, rl, rc)
    g_br = brar(gc, gh, gl, gc, length=LENGTH)["BR_20"]
    print(f"brar BR_20 on the same frame: inf={int(np.isinf(g_br).sum())} "
          f"nan={int(g_br.isna().sum())} of {len(g_br)} -- the port replaces "
          "that inf with NaN, brar does not")
    print("same frame with one bar (index 30) dipping below its prior close: "
          f"fires={int(r_out.notna().sum())} of {len(r_out)} "
          f"first={int(r_out.notna().idxmax())} "
          f"last={int(r_out.notna()[::-1].idxmax())}")
    fh, fl, fc = _frozen_frame()
    f_out = g191_110(fh, fl, fc)
    fc1 = fc.shift(1)
    f_raw = ((fh - fc1).clip(lower=0).rolling(LENGTH, min_periods=LENGTH).sum()
             / (fc1 - fl).clip(lower=0).rolling(LENGTH,
                                                min_periods=LENGTH).sum())
    print(f"frozen frame (H==L==C constant): fires={int(f_out.notna().sum())} "
          f"of {len(f_out)}; raw ratio inf on {int(np.isinf(f_raw).sum())} "
          f"bars, nan on {int(f_raw.isna().sum())} (0/0)")

    nh = high.copy()
    nh.iloc[700] = np.nan
    nan_out = g191_110(nh, low, close)
    newly_nan = int((out.notna() & nan_out.isna()).sum())
    both = out.notna() & nan_out.notna()
    mv = out.index[both & (out != nan_out)]
    print(f"one NaN in high at 700: fires={int(nan_out.notna().sum())} "
          f"newly-NaN={newly_nan} displaced={len(mv)} "
          f"first_valid={int(nan_out.notna().idxmax())}")
    nc = close.copy()
    nc.iloc[700] = np.nan
    nanc_out = g191_110(high, low, nc)
    print("one NaN in close at 700: fires="
          f"{int(nanc_out.notna().sum())} newly-NaN="
          f"{int((out.notna() & nanc_out.isna()).sum())}")

    # An all-gap-DOWN frame: no high ever clears its prior close, every low
    # breaks it, so the numerator is exactly 0 and the column is exactly 0.0.
    dclose = 100.0 - np.arange(40, dtype=float)
    dn_frame = (Series(dclose + np.r_[0.0, np.full(39, 0.5)]),
                Series(dclose - 1.0), Series(dclose))
    # high[i] = close[i-1] - 0.5 for i >= 1 (close falls by 1 per bar)
    d_out = g191_110(*dn_frame)
    dd = d_out.dropna()
    print(f"all-gap-down frame: fires={len(dd)} of 40 "
          f"all-exactly-zero={bool((dd == 0.0).all())} "
          f"nunique={int(dd.nunique())}")

    # Why `0 < length < 1` ships an all-NaN column: `int()` truncates the
    # window to 0, and a zero-width rolling sum at `min_periods=0` is not
    # NaN, it is 0.0 -- so the ratio is 0/0. Measured rather than inferred
    # from pandas' docs.
    zero_win = (high - c1).clip(lower=0).rolling(0, min_periods=0).sum()
    print(f"rolling(0, min_periods=0).sum(): nunique="
          f"{int(zero_win.nunique())} unique={sorted(set(zero_win.dropna()))[:3]} "
          f"nan={int(zero_win.isna().sum())} of {len(zero_win)}")

    # `length`'s off-nominal bands, none of them guarded.
    for bad in (0, -5, 0.5, 1):
        try:
            o = g191_110(high, low, close, length=bad)
        except Exception as exc:                      # noqa: BLE001
            print(f"length={bad!r}: raises {type(exc).__name__}: {exc}")
            continue
        if o is None:
            print(f"length={bad!r}: returns None")
            continue
        od = o.dropna()
        print(f"length={bad!r}: name={o.name} fires={int(o.notna().sum())} "
              f"nunique={int(od.nunique())} "
              f"exactly-zero={int((od == 0.0).sum())} "
              f"equals-default={bool(o.equals(out))}")

    # Warm-up boundary and the min_length guard.
    short = g191_110(high.iloc[:LENGTH], low.iloc[:LENGTH], close.iloc[:LENGTH])
    exact = g191_110(high.iloc[:LENGTH + 1], low.iloc[:LENGTH + 1],
                     close.iloc[:LENGTH + 1])
    print(f"{LENGTH} bars of history -> {short!r}; {LENGTH + 1} bars -> "
          f"fires={int(exact.notna().sum())} "
          f"first_valid={int(exact.notna().idxmax())}")
    print(f"pandas={pd.__version__} numpy={np.__version__}")


if __name__ == "__main__":
    main()
