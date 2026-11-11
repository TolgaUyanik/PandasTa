# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191055Measured.md for
`pandas_ta.momentum.g191_055`. Synthetic frames only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import importlib.util
import types
from pathlib import Path

import numpy as np
import pandas as pd
import pandas_ta as ta
from pandas import Series

from pandas_ta.momentum.g191_055 import g191_055

_REAL = importlib.import_module("pandas_ta.momentum.g191_055")

SCREEN = Path(__file__).resolve().parent / "issues" / "screen" / "ind_screen.py"


def _walk(n=1500, seed=11, sigma=0.015):
    """OHLC walk with `low <= open, close <= high` at every bar."""
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    open_ = close * (1.0 + rng.normal(0.0, sigma * 0.7, n))
    hi_body = np.maximum(open_, close)
    lo_body = np.minimum(open_, close)
    high = hi_body * (1.0 + np.abs(rng.normal(0.0, sigma * 0.5, n)))
    low = lo_body * (1.0 - np.abs(rng.normal(0.0, sigma * 0.5, n)))
    idx = pd.RangeIndex(n)
    return (Series(open_, index=idx), Series(high, index=idx),
            Series(low, index=idx), Series(close, index=idx))


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_055_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


SHIPPED_SUM = "result = swing.rolling(length, min_periods=length).sum() / close"
WRITE_SHIFT_MUTANT = (
    SHIPPED_SUM,
    "result = (swing.rolling(length, min_periods=length).sum() / close).shift(-length)",
)
CENTERED_SUM_MUTANT = (
    SHIPPED_SUM,
    "result = swing.rolling(length, center=True, min_periods=length).sum() / close",
)

OFFSETS = range(60, 1500, 40)  # past the 21-bar warm-up

#: The issue's prototype R, RETYPED from
#: `docs/issues/screen/ind_screen.py:398-405`: two branches, not three.
TWO_BRANCH_R = (
    "np.where((b > d) & (b > a), b + a / 2 + e / 4, d + e / 4)",
    "b + a / 2 + e / 4",
)


def _branches(open_, high, low, close):
    """The three branch masks of `R`, recomputed here rather than read out
    of the module, plus `R` itself."""
    c1, o1, l1 = close.shift(1), open_.shift(1), low.shift(1)
    a, b = (high - c1).abs(), (low - c1).abs()
    d, e = (high - l1).abs(), (c1 - o1).abs()
    one = (a > b) & (a > d)
    two = (~one) & (b > d) & (b > a)
    three = (~one) & (~two) & c1.notna()
    r = Series(
        np.where(one, a + b / 2 + e / 4,
                 np.where((b > d) & (b > a), b + a / 2 + e / 4, d + e / 4)),
        index=close.index,
    )
    return a, b, d, e, one, two, three, r


def _leaks(fn):
    open_, high, low, close = _walk(1500)
    oo, oh, ol, oc = _walk(1500, seed=97)
    base = fn(open_, high, low, close)
    hits = 0
    for j in OFFSETS:
        po, ph, pl, pc = open_.copy(), high.copy(), low.copy(), close.copy()
        po.iloc[j:] = oo.iloc[j:].values
        ph.iloc[j:] = oh.iloc[j:].values
        pl.iloc[j:] = ol.iloc[j:].values
        pc.iloc[j:] = oc.iloc[j:].values
        out = fn(po, ph, pl, pc)
        x, y = base.iloc[:j], out.iloc[:j]
        if not (x.isna() == y.isna()).all():
            hits += 1
            continue
        m = x.notna()
        if (x[m] != y[m]).any():
            hits += 1
    return hits


def _prototype(open_, high, low, close, length=20):
    """The issue's prototype expression, RETYPED from
    `docs/issues/screen/ind_screen.py:398-405` (with `delay`/`tsum`/`sdiv`
    from lines 45, 49 and 41), so this script works on a clone that does
    not carry the gitignored screen. TWO-branch `R`."""
    c1, o1, l1 = close.shift(1), open_.shift(1), low.shift(1)
    a, b, d = (high - c1).abs(), (low - c1).abs(), (high - l1).abs()
    e = (c1 - o1).abs()
    r = pd.Series(
        np.where((a > b) & (a > d), a + b / 2 + e / 4, b + a / 2 + e / 4),
        index=close.index,
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        si = 16 * ((close - c1 + (close - open_) / 2 + c1 - o1) / r).replace(
            [np.inf, -np.inf], np.nan) * np.maximum(a, b)
    return si.rolling(length).sum() / close


def _real_candidate(open_, high, low, close):
    """The REAL `g191_055` candidate out of the owner's screen module, when
    that (gitignored) file is present in this worktree."""
    spec = importlib.util.spec_from_file_location("_ind_screen", SCREEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ones = Series(np.ones(len(close)), index=close.index)
    return mod.REG["g191_055"]["fn"](open_, high, low, close, ones)


def main():
    print("wiring:")
    print("  g191_055 in Category['momentum']:", "g191_055" in ta.Category["momentum"])
    print("  Category total:", sum(len(v) for v in ta.Category.values()))
    print("  Category['momentum'] size:", len(ta.Category["momentum"]))

    open_, high, low, close = _walk()
    out = g191_055(open_, high, low, close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f} "
          f"negative={int((out.dropna() < 0).sum())} "
          f"positive={int((out.dropna() > 0).sum())} "
          f"zeros={int((out.dropna() == 0).sum())}")

    # OHLC consistency of the frame the claims below are measured on.
    ok = int(((low <= open_) & (open_ <= high) & (low <= close)
              & (close <= high)).sum())
    print(f"frame OHLC-consistent bars: {ok} of {n}")

    # Branch census. Branch 1 is UNREACHABLE on OHLC-consistent data (see
    # the module docstring's derivation); measured here rather than trusted.
    a, b, d, e, one, two, three, r = _branches(open_, high, low, close)
    print(f"branch census: branch1(A>B&A>D)={int(one.sum())} "
          f"branch2(B>D&B>A)={int(two.sum())} branch3(else)={int(three.sum())} "
          f"of {n - 1} bars with a prior bar")
    print(f"  the two inequalities the unreachability proof rests on: "
          f"bars with H<=C1 and B<A: {int(((high <= close.shift(1)) & (b < a)).sum())}; "
          f"bars with H>=C1 and D<A: {int(((high >= close.shift(1)) & (d < a)).sum())}")
    zero_r = int((r == 0).sum())
    zero_range = int((high == low).sum())
    print(f"  R == 0 bars: {zero_r}; zero-range (H==L) bars: {zero_range}")

    # The numerator is computed in the source's written order for FIDELITY;
    # the simplified order is algebraically equal AND measures bit-identical
    # on this walk (printed below), so the choice costs nothing here.
    c1, o1 = close.shift(1), open_.shift(1)
    src_order = close - c1 + (close - open_) / 2 + c1 - o1
    simplified = close + (close - open_) / 2 - o1
    mnum = src_order.notna()
    print("numerator source-order vs simplified (C1 cancels algebraically): "
          f"max|diff|={float((src_order[mnum] - simplified[mnum]).abs().max())!r} "
          f"bits-differ={int((src_order[mnum] != simplified[mnum]).sum())} of "
          f"{int(mnum.sum())}")

    # Gate D: price rescale, value AND selected-branch masks.
    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        ok_, hk, lk, ck = open_ * k, high * k, low * k, close * k
        scaled = g191_055(ok_, hk, lk, ck)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        _, _, _, _, one_k, two_k, three_k, _ = _branches(ok_, hk, lk, ck)
        moved = int(((one_k != one) | (two_k != two) | (three_k != three)).sum())
        print(f"x{k} PRICE max|diff|={max_diff} "
              f"relative-to-max|column|={max_diff / float(out[m].abs().max())!r} "
              f"nan-mask-match={mask_match} bars-that-changed-branch={moved}")

    # Gate A: hand-derived 5-bar example at length=2, branch 2 and branch 3
    # both exercised, including an A==B==D triple tie at bar 4.
    o5 = Series([99.0, 100.0, 99.0, 92.0, 92.5])
    h5 = Series([102.0, 103.0, 100.0, 95.0, 92.5])
    l5 = Series([95.0, 99.0, 90.0, 91.0, 92.5])
    c5 = Series([100.0, 102.0, 92.0, 94.0, 92.5])
    out5 = g191_055(o5, h5, l5, c5, length=2)
    _, _, _, _, one5, two5, three5, r5 = _branches(o5, h5, l5, c5)
    print("hand-derived 5-bar example (length=2):", out5.tolist())
    print("  R:", r5.tolist())
    print("  branch:", ["1" if one5.iloc[i] else "2" if two5.iloc[i]
                        else "3" if three5.iloc[i] else "-"
                        for i in range(len(c5))])
    # SUM over one bar, times close, is the bar's own SI.
    per_bar = g191_055(o5, h5, l5, c5, length=1) * c5
    print("  SI per bar:", per_bar.tolist())

    # Gate A: the R == 0 bar and its window. Bar 2 is zero-range, prints at
    # bar 1's low, and bar 1 opened and closed at the same price.
    o0 = Series([100.0, 99.0, 97.0, 98.0, 99.0, 100.0, 101.0])
    h0 = Series([101.0, 100.0, 97.0, 99.0, 100.0, 101.0, 102.0])
    l0 = Series([99.0, 97.0, 97.0, 97.5, 98.0, 99.0, 100.0])
    c0 = Series([100.0, 99.0, 97.0, 98.5, 99.5, 100.5, 101.5])
    _, _, _, _, _, _, _, r0 = _branches(o0, h0, l0, c0)
    out0 = g191_055(o0, h0, l0, c0, length=2)
    print(f"R==0 fixture: R={r0.tolist()}")
    print(f"  column (length=2): {out0.tolist()}")
    print(f"  R==0 at bars {[int(i) for i in r0.index[r0 == 0]]}, "
          f"NaN at bars {[int(i) for i in out0.index[out0.isna()]]}")

    # Gate A: independent per-bar replay, plain Python loop over numpy
    # scalars -- no .rolling(), no .shift(), no np.where.
    o9, h9, l9, c9 = _walk(900, seed=5)
    out9 = g191_055(o9, h9, l9, c9)
    oo, hh, ll, cc = (s.to_numpy(dtype=float) for s in (o9, h9, l9, c9))
    length = 20

    def expected_at(t):
        total = 0.0
        for i in range(t - length + 1, t + 1):  # all >= 1 since t >= length
            av, bv = abs(hh[i] - cc[i - 1]), abs(ll[i] - cc[i - 1])
            dv, ev = abs(hh[i] - ll[i - 1]), abs(cc[i - 1] - oo[i - 1])
            if av > bv and av > dv:
                rv = av + bv / 2 + ev / 4
            elif bv > dv and bv > av:
                rv = bv + av / 2 + ev / 4
            else:
                rv = dv + ev / 4
            num = cc[i] - cc[i - 1] + (cc[i] - oo[i]) / 2 + cc[i - 1] - oo[i - 1]
            total += 16 * (num / rv) * max(av, bv)
        return total / cc[t]

    for t in (300, 600, 899):
        print(f"independent-loop bar {t}: module={out9.iloc[t]!r} "
              f"loop={expected_at(t)!r}")

    # Gate A: the port (THREE-branch R) against the issue's prototype
    # (TWO-branch R), and -- when the gitignored screen is present -- the
    # REAL candidate out of its own registry. These DIFFER by design; the
    # numbers below are the size of that decision.
    proto = _prototype(open_, high, low, close)
    mm = out.notna() & proto.notna()
    print("port (3-branch R) vs retyped prototype (2-branch R): "
          f"mask-match={bool((out.isna() == proto.isna()).all())} "
          f"max|diff|={float((out[mm] - proto[mm]).abs().max())!r} "
          f"bars-differing={int((out[mm] != proto[mm]).sum())} of {int(mm.sum())} "
          f"spearman={float(out[mm].corr(proto[mm], method='spearman')):.6f}")
    # The two forms agree BIT-FOR-BIT on every branch-2 bar (where
    # `B + A/2 + E/4` is also the prototype's only live arm) and differ on
    # every branch-3 bar. Measured per bar, at length=1, where the window
    # sum is the bar's own SI; no 20-bar window on this walk is all-branch-2
    # (measured: the longest run of consecutive branch-2 bars is printed
    # below), so the per-bar form is the only way to see the agreement.
    si_port = g191_055(open_, high, low, close, length=1) * close
    si_proto = _prototype(open_, high, low, close, length=1) * close
    sm = si_port.notna() & si_proto.notna()
    run, best = 0, 0
    for flag in two.tolist():
        run = run + 1 if flag else 0
        best = max(best, run)
    print(f"  per-bar SI, branch-2 bars: {int((sm & two).sum())}, of which "
          f"bit-identical to the prototype's: "
          f"{int((si_port[sm & two] == si_proto[sm & two]).sum())}")
    print(f"  per-bar SI, branch-3 bars: {int((sm & three).sum())}, of which "
          f"bit-identical to the prototype's: "
          f"{int((si_port[sm & three] == si_proto[sm & three]).sum())}")
    print(f"  longest run of consecutive branch-2 bars: {best} (a 20-bar "
          f"window needs 20 to make the columns agree)")
    live = _load_mutant(*TWO_BRANCH_R)
    collapsed = live.g191_055(open_, high, low, close)
    mc = out.notna() & collapsed.notna()
    print("  the same comparison through a live exec'd mutant of the module "
          f"with the third branch collapsed: max|diff|="
          f"{float((out[mc] - collapsed[mc]).abs().max())!r} "
          f"bit-equal-to-retyped-prototype="
          f"{bool((collapsed[mc] == proto[mc]).all())}")
    if SCREEN.exists():
        cand = _real_candidate(open_, high, low, close)
        mk = out.notna() & cand.notna()
        print("port vs REAL screen candidate (2-branch): "
              f"mask-match={bool((out.isna() == cand.isna()).all())} "
              f"max|diff|={float((out[mk] - cand[mk]).abs().max())!r} "
              f"spearman={float(out[mk].corr(cand[mk], method='spearman')):.6f}")
        print("retyped prototype vs REAL screen candidate: "
              f"mask-match={bool((proto.isna() == cand.isna()).all())} "
              f"max|diff|={float((proto[mk] - cand[mk]).abs().max())!r}")
    else:
        print("port vs REAL screen candidate: SKIPPED, "
              f"{SCREEN} absent (gitignored)")

    # Gate B: future-perturbation leak counts, real module vs. two mutants.
    total = len(list(OFFSETS))
    print(f"real-module leaks: {_leaks(g191_055)} of {total}")
    for label, mut in (("write-shift", WRITE_SHIFT_MUTANT),
                       ("centered-sum", CENTERED_SUM_MUTANT)):
        mod = _load_mutant(*mut)
        live_differs = not mod.g191_055(open_, high, low, close).equals(out)
        print(f"{label} mutant: live-differs={live_differs} "
              f"leaks={_leaks(mod.g191_055)} of {total}")

    # Non-redundancy against the nearest shipped columns, on a 900-bar frame
    # (a synthetic stand-in, NOT Gate E -- Gate E is the launcher's run).
    df = pd.DataFrame({"open": o9, "high": h9, "low": l9, "close": c9,
                       "volume": Series(np.full(len(c9), 1e6), index=c9.index)})
    own = g191_055(o9, h9, l9, c9)
    others = {
        # the open-anchored directional GTJA191 ports already in the fork
        "G191_069_20": df.ta.g191_069(),
        "G191_093_20": df.ta.g191_093(),
        "G191_187_20": df.ta.g191_187(),
        "bias:BIAS_SMA_26": df.ta.bias(),
        "ROC_10": df.ta.roc(),
        "G191_003_6": df.ta.g191_003(),
        "BOP": df.ta.bop(),
        "CCI_14_0.015": df.ta.cci(),
    }
    for name, col in others.items():
        msk = own.notna() & col.notna()
        rho = float(own[msk].corr(col[msk], method="spearman"))
        print(f"spearman vs {name} ({col.name}): {rho:.6f} (n={int(msk.sum())})")


if __name__ == "__main__":
    main()
