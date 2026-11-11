# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191003Measured.md for
`pandas_ta.momentum.g191_003`. Synthetic frames only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import importlib.util
import types
from pathlib import Path

import numpy as np
import pandas as pd
import pandas_ta as ta
from pandas import Series

from pandas_ta.momentum.g191_003 import g191_003

_REAL = importlib.import_module("pandas_ta.momentum.g191_003")

SCREEN = Path(__file__).resolve().parent / "issues" / "screen" / "ind_screen.py"


def _walk(n=1500, seed=11, sigma=0.015):
    """High/low/close walk with `low <= close <= high` at every bar."""
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    high = close * (1.0 + np.abs(rng.normal(0.0, sigma * 0.5, n)))
    low = close * (1.0 - np.abs(rng.normal(0.0, sigma * 0.5, n)))
    idx = pd.RangeIndex(n)
    return Series(high, index=idx), Series(low, index=idx), Series(close, index=idx)


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_003_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


SHIPPED_SUM = "result = bar.rolling(length, min_periods=length).sum() / close"
WRITE_SHIFT_MUTANT = (
    SHIPPED_SUM,
    "result = (bar.rolling(length, min_periods=length).sum() / close).shift(-length)",
)
CENTERED_SUM_MUTANT = (
    SHIPPED_SUM,
    "result = bar.rolling(length, center=True, min_periods=length).sum() / close",
)
NO_TERNARY_MUTANT = (
    "np.where(close == prev_close, 0.0, close - ref)",
    "(close - ref)",  # the `C=C1 ? 0 :` branch deleted
)

OFFSETS = range(50, 1500, 40)  # past the 7-bar warm-up


def _leaks(fn):
    high, low, close = _walk(1500)
    other_h, other_l, other_c = _walk(1500, seed=97)
    base = fn(high, low, close)
    hits = 0
    for j in OFFSETS:
        ph, pl, pc = high.copy(), low.copy(), close.copy()
        ph.iloc[j:] = other_h.iloc[j:].values
        pl.iloc[j:] = other_l.iloc[j:].values
        pc.iloc[j:] = other_c.iloc[j:].values
        out = fn(ph, pl, pc)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def _prototype(high, low, close, length=6):
    """The issue's prototype expression, RETYPED from
    `docs/issues/screen/ind_screen.py:282-287` (with `delay`/`tsum` from
    lines 45 and 49), so this script works on a clone that does not carry
    the gitignored screen."""
    c1 = close.shift(1)
    x = np.where(
        close == c1,
        0.0,
        close - np.where(close > c1, np.minimum(low, c1), np.maximum(high, c1)),
    )
    return pd.Series(x, index=close.index).where(c1.notna()).rolling(length).sum() / close


def _real_candidate(high, low, close):
    """The REAL `g191_003` candidate out of the owner's screen module, when
    that (gitignored) file is present in this worktree."""
    spec = importlib.util.spec_from_file_location("_ind_screen", SCREEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ones = Series(np.ones(len(close)), index=close.index)
    return mod.REG["g191_003"]["fn"](close, high, low, close, ones)


def main():
    print("wiring:")
    print("  g191_003 in Category['momentum']:", "g191_003" in ta.Category["momentum"])
    print("  Category total:", sum(len(v) for v in ta.Category.values()))
    print("  Category['momentum'] size:", len(ta.Category["momentum"]))

    high, low, close = _walk()
    out = g191_003(high, low, close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f} "
          f"negative={int((out.dropna() < 0).sum())} "
          f"positive={int((out.dropna() > 0).sum())}")

    # Branch census on this walk: up / down / flat (the `C=C1` zero branch).
    prev = close.shift(1)
    up_mask, down_mask = (close > prev), ((close < prev) & prev.notna())
    flat_mask = (close == prev) & prev.notna()
    up, down, flat = int(up_mask.sum()), int(down_mask.sum()), int(flat_mask.sum())
    print(f"branch census: up={up} down={down} flat(C==C1)={flat} "
          f"of {n} bars (bar 0 has no C1)")

    # Per-bar sign: up bars must contribute > 0, down bars < 0 (module
    # docstring's PER-BAR SIGN claim), measured rather than assumed.
    ref = np.where(close > prev, np.minimum(low, prev), np.maximum(high, prev))
    contrib = Series(np.where(close == prev, 0.0, close - ref),
                     index=close.index).where(prev.notna())
    print(f"sign: up bars with contribution <= 0: "
          f"{int((contrib[up_mask] <= 0).sum())} of {up}; "
          f"down bars with contribution >= 0: "
          f"{int((contrib[down_mask] >= 0).sum())} of {down}")

    # Gate D: price rescale. Both the value and the BRANCH MASKS, since the
    # branch tests are exact float comparisons.
    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        hk, lk, ck = high * k, low * k, close * k
        scaled = g191_003(hk, lk, ck)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        pk = ck.shift(1)
        up_k, eq_k = (ck > pk), (ck == pk)
        branch_moved = int(((up_k != up_mask) | (eq_k != (close == prev))).sum())
        print(f"x{k} PRICE max|diff|={max_diff} nan-mask-match={mask_match} "
              f"bars-that-changed-branch={branch_moved}")

    # Gate A: hand-derived 7-bar example at length=3.
    h7 = Series([10.0, 13.0, 12.0, 16.0, 11.0, 21.0, 10.0])
    l7 = Series([8.0, 9.0, 8.0, 11.0, 7.0, 15.0, 6.0])
    c7 = Series([9.0, 12.0, 9.0, 15.0, 8.0, 20.0, 7.0])
    out7 = g191_003(h7, l7, c7, length=3)
    print("hand-derived 7-bar example (length=3):", out7.tolist())
    p7 = c7.shift(1)
    r7 = np.where(c7 > p7, np.minimum(l7, p7), np.maximum(h7, p7))
    print("  per-bar contribution:",
          Series(np.where(c7 == p7, 0.0, c7 - r7),
                 index=c7.index).where(p7.notna()).tolist())

    # Gate A: the `C=C1 ? 0` branch is NOT redundant. A frame with one bar
    # whose close exactly repeats the prior close, shipped module vs. the
    # same source with that branch deleted (live exec'd mutant).
    h5 = Series([10.0, 12.0, 14.0, 13.0, 16.0, 15.0, 18.0, 17.0])
    l5 = Series([8.0, 9.0, 10.0, 9.0, 11.0, 10.0, 12.0, 11.0])
    c5 = Series([9.0, 11.0, 11.0, 12.0, 14.0, 13.0, 15.0, 14.0])
    no_ternary = _load_mutant(*NO_TERNARY_MUTANT)
    ship5 = g191_003(h5, l5, c5, length=3)
    mut5 = no_ternary.g191_003(h5, l5, c5, length=3)
    flat_bars = [int(i) for i in c5.index[(c5 == c5.shift(1))]]
    print(f"flat-close fixture: flat bars at {flat_bars}")
    print("  shipped (with the zero branch):", ship5.tolist())
    print("  mutant (zero branch deleted):  ", mut5.tolist())
    print("  differ:", not ship5.equals(mut5))

    # Gate A: the third value the column can take. A window whose closes
    # are all flat sums to exactly 0.0 -- every contribution a literal
    # 0.0, so the sum is bit-exact. The 1,500-bar walk never reaches it.
    flat_close = Series([100.0] * 7)
    flat_out = g191_003(
        Series([101.0, 102.0, 103.0, 101.5, 104.0, 102.5, 105.0]),
        Series([99.0, 98.0, 97.0, 98.5, 96.0, 97.5, 95.0]),
        flat_close,
    )
    print("all-flat 7-bar frame (defaults):", flat_out.tolist())
    print(f"  bar 6 == 0.0 exactly: {flat_out.iloc[6] == 0.0}")

    # Gate A: independent per-bar replay with plain numpy slicing, not
    # pandas' own .rolling()/.shift(), at the shipped default.
    h9, l9, c9 = _walk(900, seed=5)
    out9 = g191_003(h9, l9, c9)
    hh, ll, cc = (s.to_numpy(dtype=float) for s in (h9, l9, c9))
    length = 6

    def expected_at(t):
        total = 0.0
        for i in range(t - length + 1, t + 1):
            c, c1 = cc[i], cc[i - 1]
            if c == c1:
                continue
            r = min(ll[i], c1) if c > c1 else max(hh[i], c1)
            total += c - r
        return total / cc[t]

    for t in (300, 600, 899):
        print(f"independent-loop bar {t}: module={out9.iloc[t]!r} "
              f"loop={expected_at(t)!r}")

    # Gate A: the retyped prototype expression, and -- when the gitignored
    # screen is present -- the REAL candidate out of its own registry.
    proto = _prototype(high, low, close)
    print("port vs retyped prototype: mask-match="
          f"{bool((out.isna() == proto.isna()).all())} "
          f"max|diff|={float((out[m] - proto[m]).abs().max())!r}")
    if SCREEN.exists():
        cand = _real_candidate(high, low, close)
        print("port vs REAL screen candidate: mask-match="
              f"{bool((out.isna() == cand.isna()).all())} "
              f"max|diff|={float((out[m] - cand[m]).abs().max())!r}")
        print("retyped vs REAL screen candidate: mask-match="
              f"{bool((proto.isna() == cand.isna()).all())} "
              f"max|diff|={float((proto[m] - cand[m]).abs().max())!r}")
    else:
        print("port vs REAL screen candidate: SKIPPED, "
              f"{SCREEN} absent (gitignored)")

    # Gate B: future-perturbation leak counts, real module vs. two mutants.
    total = len(list(OFFSETS))
    print(f"real-module leaks: {_leaks(g191_003)} of {total}")
    for label, mut in (("write-shift", WRITE_SHIFT_MUTANT),
                       ("centered-sum", CENTERED_SUM_MUTANT)):
        mod = _load_mutant(*mut)
        live = not mod.g191_003(high, low, close).equals(out)
        print(f"{label} mutant: live-differs={live} leaks={_leaks(mod.g191_003)} "
              f"of {total}")

    # Non-redundancy against the nearest shipped columns, on a 900-bar frame
    # (a synthetic stand-in, NOT Gate E -- Gate E is the launcher's run).
    df = pd.DataFrame({"open": c9, "high": h9, "low": l9, "close": c9,
                       "volume": Series(np.full(len(c9), 1e6), index=c9.index)})
    own = g191_003(h9, l9, c9)
    others = {
        "kdj:J_9_3": df.ta.kdj()["J_9_3"],
        "G191_129_12": df.ta.g191_129(),
        "WILLR_14": df.ta.willr(),
        "AD": df.ta.ad(),
        "CMF_20": df.ta.cmf(),
    }
    for name, col in others.items():
        mm = own.notna() & col.notna()
        rho = float(own[mm].corr(col[mm], method="spearman"))
        print(f"spearman vs {name}: {rho:.6f} (n={int(mm.sum())})")


if __name__ == "__main__":
    main()
