# -*- coding: utf-8 -*-
"""Reproduce every number in docs/TsPeaks20Measured.md for `ts_peaks_20`
(PandasTa issue #92, TS-PEAKS-20).

Run from the repository root:

    python docs/measure_ts_peaks_20.py            # every section
    python docs/measure_ts_peaks_20.py gate_a     # one section

Gates A-D and the synthetic reachability only. Gate E needs the private
Backtesting engine and the 89 frozen ALTPORT-1 BIST frames, which are not in
this worktree; the launcher runs it after the porting session.
"""
import importlib
import itertools
import sys
import time
import tracemalloc
import types

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.statistics.ts_peaks_20 import ts_peaks_20

LENGTH = 20
REAL = importlib.import_module("pandas_ta.statistics.ts_peaks_20")
SUPPORT = REAL.SUPPORT
CANDIDATES = LENGTH - 2 * SUPPORT  # 16


def head(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


# ------------------------------------------------------------------ frames


def walk(n=1500, seed=11, sigma=0.015, drift=0.0):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(drift, sigma, n))))


def tick_rounded(n=1500, seed=55):
    """Two-decimal prices: consecutive closes TIE, which is the regime the
    strict `>` decides."""
    return Series(np.round(walk(n, seed).to_numpy(), 2))


def coarse_grid(n=1500, seed=55, sigma=0.002, decimals=1):
    """A quiet path on a COARSE price grid: a large share of candidates tie
    with a neighbour, so `>` and `>=` part company here."""
    return Series(np.round(walk(n, seed, sigma).to_numpy(), decimals))


def from_returns(r):
    return Series(100.0 * np.cumprod(1.0 + np.asarray(r, dtype=float)))


def heavy_tailed(n=1500, seed=3, df=2.0, sigma=0.01):
    rng = np.random.default_rng(seed)
    return from_returns(np.clip(sigma * rng.standard_t(df, n), -0.5, 0.5))


def two_point(n=1500, seed=4, sigma=0.01):
    rng = np.random.default_rng(seed)
    return from_returns(np.where(rng.random(n) < 0.5, sigma, -sigma))


def mean_reverting(n=1500, seed=7, sigma=0.01, phi=-0.6):
    """An AR(1) on the returns with NEGATIVE phi: up follows down, so peaks
    are as dense as a path allows."""
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    r = np.zeros(n)
    for t in range(1, n):
        r[t] = phi * r[t - 1] + e[t]
    return from_returns(np.clip(r, -0.5, 0.5))


def trending(n=1500, seed=9, sigma=0.004, drift=0.01):
    return walk(n, seed, sigma, drift)


def flat(n=300, price=100.0):
    return Series(np.full(n, price))


def monotone(n=300, step=0.5, price=100.0):
    return Series(price + step * np.arange(n))


def falling(n=300, step=0.5, price=400.0):
    return Series(price - step * np.arange(n))


def zigzag(n=300, lo=100.0, hi=101.0):
    return Series(np.where(np.arange(n) % 2 == 0, lo, hi))


FRAMES = {
    "walk": walk,
    "tick-rounded": tick_rounded,
    "coarse-grid": coarse_grid,
    "heavy-tailed": heavy_tailed,
    "mean-reverting": mean_reverting,
    "trending": trending,
    "two-point": two_point,
}


def compare(name, a, b):
    """Max |difference|, bit-equal count and Spearman over the shared non-NaN
    bars, plus whether the NaN masks agree."""
    masks_agree = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    x, y = a[m], b[m]
    diff = (x - y).abs()
    bit = int((x == y).sum())
    constant = int(x.nunique()) < 2 or int(y.nunique()) < 2
    rho = (float("nan") if constant or len(x) < 3
           else float(x.corr(y, method="spearman")))
    rho_text = "constant" if constant else f"{rho:.6f}"
    print(f"  {name}: n={int(m.sum())} max|diff|={float(diff.max()):.6e} "
          f"bit-equal={bit}/{int(m.sum())} spearman={rho_text} "
          f"distinct={int(x.nunique())}/{int(y.nunique())} "
          f"nan-masks-agree={masks_agree}")
    return float(diff.max()), bit, rho, masks_agree


# ---------------------------------------------------------------- the source


def tsfresh_installed():
    try:
        importlib.import_module("tsfresh.feature_extraction.feature_calculators")
    except Exception as exc:  # noqa: BLE001 -- the reason is the measurement
        return f"NOT importable: {type(exc).__name__}: {exc}"
    return "importable"


def number_peaks(x, n=SUPPORT):
    """`number_peaks` as the published definition spells it, with `np.roll`:

        x_reduced = x[n:-n]
        res = None
        for i in range(1, n + 1):
            result_first = x_reduced > roll(x, i)[n:-n]
            res = result_first if res is None else res & result_first
            res &= x_reduced > roll(x, -i)[n:-n]
        return sum(res)

    `np.roll` WRAPS, and this measures that the wrap never reaches the kept
    slice: for j in [n, len - n) and i in [1, n], both j - i and j + i stay
    inside [0, len), so no wrapped element is ever compared (asserted in
    `roll_never_wraps` below).
    """
    x = np.asarray(x, dtype=float)
    x_reduced = x[n:-n]
    res = None
    for i in range(1, n + 1):
        first = x_reduced > np.roll(x, i)[n:-n]
        res = first if res is None else (res & first)
        res &= x_reduced > np.roll(x, -i)[n:-n]
    return int(np.sum(res))


def roll_never_wraps(length=LENGTH, n=SUPPORT):
    """The indices `number_peaks` actually reads, enumerated."""
    bad = []
    for j in range(n, length - n):
        for i in range(1, n + 1):
            for k in (j - i, j + i):
                if not 0 <= k < length:
                    bad.append((j, i, k))
    return bad


def roll_oracle(close, length=LENGTH, n=SUPPORT):
    """`number_peaks` run window by window, sharing no code with the module."""
    c = close.to_numpy(dtype=float)
    out = np.full(c.size, np.nan)
    for t in range(length - 1, c.size):
        w = c[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        out[t] = number_peaks(w, n)
    return Series(out, index=close.index)


def scalar_loop(close, length=LENGTH, n=SUPPORT):
    """An independent per-window loop in plain Python scalars."""
    c = [float(v) for v in close.to_numpy(dtype=float)]
    out = [float("nan")] * len(c)
    for t in range(length - 1, len(c)):
        w = c[t - length + 1:t + 1]
        if any(v != v or v in (float("inf"), float("-inf")) for v in w):
            continue
        total = 0
        for j in range(n, len(w) - n):
            if all(w[j] > w[j + d] for d in range(-n, n + 1) if d != 0):
                total += 1
        out[t] = float(total)
    return Series(out, index=close.index)


def screen_candidate():
    """`REG["ts_peaks_20"]["fn"]` out of the screen's own registry, when this
    worktree has `docs/issues/` (gitignored, so a clone does not)."""
    import importlib.util
    from pathlib import Path

    # Anchored on this file, not on the working directory: a CWD-relative
    # path would print "absent" instead of failing when the script is run
    # from elsewhere, and A2's evidence would quietly disappear.
    path = Path(__file__).resolve().parents[1] / "docs" / "issues" / \
        "screen" / "ind_screen.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("_ind_screen", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_ind_screen"] = mod
    spec.loader.exec_module(mod)
    return mod.REG["ts_peaks_20"]["fn"]


def prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py` candidate `ts_peaks_20`, retyped
    verbatim because that tree is gitignored:

        @cand("ts_peaks_20", "confirmed local peaks of close (20, support 2)",
              TS, "number_peaks(x, n=2) on 20 closes; a peak counts once
              confirmed 2 bars later")
        def _(o, h, l, c, v):
            x = c.shift(2)            # candidate peak bar, confirmed today
            pk = (x > c.shift(3)) & (x > c.shift(4)) & (x > c.shift(1)) & (x > c)
            return pk.astype(float).rolling(16).sum().where(c.shift(19).notna())
    """
    c = close
    x = c.shift(2)
    pk = (x > c.shift(3)) & (x > c.shift(4)) & (x > c.shift(1)) & (x > c)
    return pk.astype(float).rolling(length - 2 * SUPPORT).sum().where(
        c.shift(length - 1).notna())


def variant(close, length=LENGTH, support=SUPPORT, far_only=False,
            non_strict=False, candidates_window=False, share=False,
            mirrored=False, on_returns=False, no_confirm=False):
    """The module's arithmetic with one reading changed, so the cost of each
    decision is a measurement rather than an argument.

    `no_confirm` drops the forward confirmation and keeps everything else: a
    candidate counts if it is above its two PRECEDING closes only, over the
    SAME 16 candidate positions (bars T-17 .. T-2) and the same warm-up. It
    is NOT a same-bar column: the newest candidate is still bar T-2 and
    today's close is never counted -- bar T still produces a value, it just
    cannot contain itself. It prices the confirmation at a FIXED lag, which
    is the comparison worth making.
    """
    c = close.to_numpy(dtype=float)
    if on_returns:
        r = np.full(c.size, np.nan)
        r[1:] = c[1:] / c[:-1] - 1.0
        c = r
    if mirrored:
        c = -c
    n = c.size
    pad = support
    core = c[pad:n - pad]
    ok = np.isfinite(c)
    peak = np.ones(core.size, dtype=bool)
    valid = ok[pad:n - pad].copy()
    distances = [support] if far_only else list(range(1, support + 1))
    for i in distances:
        left, right = c[pad - i:n - pad - i], c[pad + i:n - pad + i]
        with np.errstate(invalid="ignore"):
            if no_confirm:
                hit = (core > left)
            elif non_strict:
                hit = (core >= left) & (core >= right)
            else:
                hit = (core > left) & (core > right)
        peak &= hit
        valid &= ok[pad - i:n - pad - i] & ok[pad + i:n - pad + i]
    flags = np.where(valid, peak.astype(np.int8), np.int8(-1))
    cands = length if candidates_window else length - 2 * pad
    if flags.size < cands:
        return Series(np.full(c.size, np.nan), index=close.index)
    windows = sliding_window_view(flags, cands)
    counts = windows.sum(axis=1, dtype=np.int64).astype(float)
    if share:
        counts = counts / cands
    bad = (windows < 0).any(axis=1)
    out = np.full(c.size, np.nan)
    # Row r's newest candidate is bar r + cands - 1 + pad, so its bar is that
    # plus `pad`.
    out[cands + 2 * pad - 1:] = np.where(bad, np.nan, counts)
    return Series(out, index=close.index)


def source():
    head("The source formula")
    print(f"  tsfresh in this worktree: {tsfresh_installed()}")
    print(f"  support n = {SUPPORT}, window {LENGTH} closes, "
          f"{CANDIDATES} candidates a window")
    print("\n  the comparisons a candidate at window position j must win, "
          "n = 2:")
    print("    j > j-1, j > j-2, j > j+1, j > j+2   "
          "(`for i in range(1, n + 1)`, both sides)")
    print(f"  candidate window positions: "
          f"{list(range(SUPPORT, LENGTH - SUPPORT))}")
    print(f"  the newest candidate is window position {LENGTH - SUPPORT - 1}"
          f", i.e. bar T-{SUPPORT}: the issue's 'confirmed 2 bars later'")
    print(f"\n  np.roll's wrap never reaches the kept slice -- offending "
          f"(j, i, index) triples: {roll_never_wraps()}")
    print("\n  the screen prototype's four comparisons, for contrast:")
    print("    pk = (x > c.shift(3)) & (x > c.shift(4)) & (x > c.shift(1)) "
          "& (x > c), x = c.shift(2)")
    print("    -- the same four, so unlike issue #91's ts_perment_20 the "
          "prototype and the\n       source formula agree here (measured in "
          "A2)")


# ----------------------------------------------------------------- Gate A


def peaks_of(w):
    """Window positions that are peaks, by the scalar definition."""
    w = [float(v) for v in w]
    return [j for j in range(SUPPORT, len(w) - SUPPORT)
            if all(w[j] > w[j + d] for d in range(-SUPPORT, SUPPORT + 1)
                   if d != 0)]


SIX_WITNESS = [1.0, 1.0, 2.0, 1.0, 1.0, 2.0, 1.0, 1.0, 2.0,
               1.0, 1.0, 2.0, 1.0, 1.0, 2.0, 1.0, 1.0, 2.0, 1.0, 1.0]


def max_peaks_exhaustive(candidates=CANDIDATES, span=3):
    """The ceiling, exhaustively: two peaks cannot be closer than 3 bars (a
    peak is strictly above the close two bars either side, so of two bars 1
    or 2 apart each would have to be above the other), so the count is at
    most the largest subset of the 16 candidate positions that is pairwise at
    least 3 apart. Enumerated over all 2**16 subsets."""
    by_size, checked = {}, 0
    for mask in range(1 << candidates):
        checked += 1
        chosen = [j for j in range(candidates) if mask >> j & 1]
        if any(chosen[k + 1] - chosen[k] < span
               for k in range(len(chosen) - 1)):
            continue
        by_size.setdefault(len(chosen), []).append(
            tuple(j + SUPPORT for j in chosen))
    best = max(by_size)
    return best, sorted(by_size[best]), checked


def gate_a():
    head("Gate A -- correctness")

    print("\nA1. Hand-derived windows against the module")
    cases = [
        ("20 identical closes (strict `>`: a plateau is not a peak)",
         flat(LENGTH), LENGTH, 0.0),
        ("20 strictly rising closes", monotone(LENGTH), LENGTH, 0.0),
        ("20 strictly falling closes", falling(LENGTH), LENGTH, 0.0),
        ("zigzag 100/101 x 20 (no close beats the one TWO bars away)",
         zigzag(LENGTH), LENGTH, 0.0),
        ("the six-peak witness [1,1,2]*6 + [1,1]", Series(SIX_WITNESS),
         LENGTH, 6.0),
        ("length 5, closes [1,2,5,2,1]: one candidate, a peak",
         Series([1.0, 2.0, 5.0, 2.0, 1.0]), 5, 1.0),
        ("length 5, closes [1,2,3,4,5]: one candidate, not a peak",
         Series([1.0, 2.0, 3.0, 4.0, 5.0]), 5, 0.0),
        ("length 9, closes [1,2,9,2,1,2,9,2,1]: two peaks",
         Series([1.0, 2.0, 9.0, 2.0, 1.0, 2.0, 9.0, 2.0, 1.0]), 9, 2.0),
    ]
    for name, close, length, want in cases:
        got = ts_peaks_20(close, length=length)
        v = float(got.iloc[length - 1])
        print(f"  {name}\n    module={v!r} hand={want!r} "
              f"peak positions={peaks_of(close.to_numpy()[-length:])} "
              f"name={got.name}")

    print("\nA2. The screen prototype (retyped, and imported from the "
          "owner's tree)")
    for frame in ("walk", "tick-rounded", "coarse-grid", "two-point"):
        close = FRAMES[frame]()
        print(f"  {frame}:")
        compare("    port vs the prototype retyped", ts_peaks_20(close),
                prototype(close))
        fn = screen_candidate()
        if fn is None:
            print("    the screen registry is absent from this worktree")
        else:
            imported = fn(close, close, close, close, close)
            compare("    port vs the IMPORTED candidate", ts_peaks_20(close),
                    Series(np.asarray(imported, dtype=float),
                           index=close.index))
    print("\n  ...on CLEAN frames. Where a close is not finite the two part "
          "company: the\n  prototype's comparisons are False at a NaN and its "
          "rolling sum still emits a\n  number, so it UNDERCOUNTS where this "
          "port refuses:")
    close = walk(400, seed=3)
    c = close.to_numpy().copy()
    c[200] = np.nan
    holed = Series(c, index=close.index)
    port, proto = ts_peaks_20(holed), prototype(holed)
    disagree = int((port.isna() & proto.notna()).sum())
    both = port.notna() & proto.notna()
    print(f"    one NaN at bar 200 of a 400-bar walk: port NaN where the "
          f"prototype emits a number: {disagree} bars "
          f"{[int(i) for i in np.flatnonzero((port.isna() & proto.notna()).to_numpy())][:3]}...")
    print(f"    on the bars where both fire they still agree: "
          f"{int((port[both] == proto[both]).sum())}/{int(both.sum())}")

    print("\nA3. The np.roll spelling of number_peaks, window by window")
    for frame in ("walk", "tick-rounded", "coarse-grid", "two-point"):
        close = FRAMES[frame](n=600)
        compare(f"  {frame}", ts_peaks_20(close), roll_oracle(close))

    print("\nA4. An independent plain-Python scalar loop")
    for frame in ("walk", "tick-rounded", "coarse-grid"):
        close = FRAMES[frame](n=600)
        compare(f"  {frame}", ts_peaks_20(close), scalar_loop(close))

    print("\nA5. The open readings, priced on a walk, a tick-rounded walk "
          "and a coarse grid")
    for frame in ("walk", "tick-rounded", "coarse-grid"):
        close = FRAMES[frame]()
        port = ts_peaks_20(close)
        print(f"  {frame}:")
        compare("    support on BOTH sides at 1 AND 2. Rejected: only the "
                "closes 2 away",
                port, variant(close, far_only=True))
        compare("    support 2. Rejected: support 1 (immediate neighbours "
                "only)",
                port, variant(close, support=1))
        compare("    STRICT >. Rejected: >= (a plateau becomes a peak)",
                port, variant(close, non_strict=True))
        compare("    the window is 20 CLOSES (16 candidates). Rejected: 20 "
                "candidates (24 closes)",
                port, variant(close, candidates_window=True))
        share_rho = compare(
            "    the raw COUNT. Rejected: the share of the 16 candidates",
            port, variant(close, share=True))[2]
        print(f"      that Spearman to every digit pandas gives: "
              f"{share_rho!r}")
        compare("    PEAKS of close. Rejected: peaks of -close (troughs)",
                port, variant(close, mirrored=True))
        compare("    peaks of the CLOSES. Rejected: peaks of the RETURN "
                "series at the same 16 positions",
                port, variant(close, on_returns=True))
        compare("    the 2-bar CONFIRMATION. Rejected: NO confirmation, the "
                "same 16 candidate positions",
                port, variant(close, no_confirm=True))
    print("  tie rate (share of candidates tied with a neighbour within "
          "+/-2):")
    for frame in sorted(FRAMES):
        c = FRAMES[frame]().to_numpy()
        core = c[SUPPORT:c.size - SUPPORT]
        tied = np.zeros(core.size, dtype=bool)
        for d in (-2, -1, 1, 2):
            tied |= core == c[SUPPORT + d:c.size - SUPPORT + d]
        print(f"    {frame}: {float(tied.mean()):.6f} "
              f"({int(tied.sum())} of {tied.size} candidates)")

    print("\nA6. The ceiling: 6 at length 20, and it is attained")
    best, winners, checked = max_peaks_exhaustive()
    print(f"  largest pairwise-3-apart subset of the 16 candidate positions: "
          f"{best}")
    print(f"  how many subsets attain it: {len(winners)} -- {winners}")
    print(f"  subsets enumerated: {checked} (= 2**{CANDIDATES})")
    print(f"  the witness {SIX_WITNESS} has peaks at "
          f"{peaks_of(SIX_WITNESS)}, module reads "
          f"{float(ts_peaks_20(Series(SIX_WITNESS)).iloc[LENGTH - 1])!r}")
    print("  no close 1 or 2 apart can both be peaks -- checked over every "
          "pair of\n  candidate positions by construction above; and over "
          "random windows:")
    rng = np.random.default_rng(2026)
    worst, seen = 0, set()
    for _ in range(200000):
        w = rng.permutation(np.arange(1.0, LENGTH + 1.0))
        p = peaks_of(w)
        seen.add(len(p))
        worst = max(worst, len(p))
        for a, b in itertools.combinations(p, 2):
            assert b - a >= 3, (w, p)
    print(f"    200,000 random orderings of 20 distinct closes: counts seen "
          f"{sorted(seen)}, max {worst}")


# ----------------------------------------------------------------- Gate B


BACK_DATE_TWO = (
    "    out[length - 1:] = np.where(bad, np.nan, counts)",
    "    out[length - 3:n - 2] = np.where(bad, np.nan, counts)")
BACK_DATE_FULL = (
    "    out[length - 1:] = np.where(bad, np.nan, counts)",
    "    out[:windows.shape[0]] = np.where(bad, np.nan, counts)")
FORWARD_FLAG = (
    "    windows = sliding_window_view(flags, candidates)",
    "    windows = sliding_window_view(np.roll(flags, -1), candidates)")
ROLLED_WINDOW = (
    "    windows = sliding_window_view(flags, candidates)",
    "    windows = sliding_window_view(np.roll(flags, -(length // 2)), "
    "candidates)")
FORWARD_LEG = (
    "        left, right = c[SUPPORT - i:n - SUPPORT - i], c[SUPPORT + i:n - SUPPORT + i]",
    "        left, right = c[SUPPORT - i:n - SUPPORT - i], np.roll(c, -1)[SUPPORT + i:n - SUPPORT + i]")

MUTANTS = [BACK_DATE_TWO, BACK_DATE_FULL, FORWARD_FLAG, ROLLED_WINDOW,
           FORWARD_LEG]
MUTANT_IDS = ["back_date_two", "back_date_full", "forward_flag",
              "rolled_window", "forward_leg"]
OFFSETS = range(40, 1500, 40)
PAIRS = {
    "walk": (walk(), walk(seed=97)),
    "tick-rounded": (tick_rounded(), tick_rounded(seed=56)),
    "heavy-tailed": (heavy_tailed(), heavy_tailed(seed=8)),
}


def load_mutant(old, new):
    src = open(REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_peaks_20_mutant")
    mod.__file__ = REAL.__file__
    exec(compile(src.replace(old, new), REAL.__file__, "exec"), mod.__dict__)
    return mod


def caught_offsets(fn, close, other):
    base = fn(close)
    hits = []
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        out = fn(p)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits.append(j)
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits.append(j)
    return hits


def missed(fn, close, other):
    hits = set(caught_offsets(fn, close, other))
    return [j for j in OFFSETS if j not in hits]


def gate_b():
    head("Gate B -- causality, by mutant")
    n = len(list(OFFSETS))
    print(f"  {n} offsets, J = 40 .. 1480 step 40; a hit means a bar "
          f"STRICTLY BEFORE J moved")

    print("\n  the real module, and each mutant, on three frames")
    for frame in sorted(PAIRS):
        close, other = PAIRS[frame]
        print(f"    real module, {frame}: "
              f"{len(caught_offsets(ts_peaks_20, close, other))}/{n}")
    for i, (old, new) in enumerate(MUTANTS):
        mod = load_mutant(old, new)
        for frame in sorted(PAIRS):
            close, other = PAIRS[frame]
            live = not mod.ts_peaks_20(close).equals(ts_peaks_20(close))
            hits = caught_offsets(mod.ts_peaks_20, close, other)
            print(f"    {MUTANT_IDS[i]}, {frame}: {len(hits)}/{n} "
                  f"missed={[j for j in OFFSETS if j not in set(hits)]} "
                  f"live-mutation={live}")

    print("\n  the same five mutants at non-default lengths, on the walk")
    close, other = PAIRS["walk"]
    for length in (10, 60, 5):
        def real(c, length=length):
            return ts_peaks_20(c, length=length)
        first = int(real(close).notna().to_numpy().argmax())
        print(f"    length={length}: real module "
              f"{len(caught_offsets(real, close, other))}/{n}, first value "
              f"at bar {first}")
        for i, (old, new) in enumerate(MUTANTS):
            mod = load_mutant(old, new)

            def mutated(c, mod=mod, length=length):
                return mod.ts_peaks_20(c, length=length)
            hits = caught_offsets(mutated, close, other)
            live = not mutated(close).equals(real(close))
            print(f"      {MUTANT_IDS[i]}: {len(hits)}/{n} "
                  f"missed={[j for j in OFFSETS if j not in set(hits)]} "
                  f"live-mutation={live}")

    print("\n  WHY a one-bar leak is missed at most offsets, measured "
          "exactly.")
    print("  `forward_flag` rolls the flag array one candidate forward, so "
          "bar T reads the\n  candidates at bars T-16 .. T-1 instead of "
          "T-17 .. T-2. At offset J the only\n  prefix bar that can move is "
          "J-1, and the only candidate of ITS window that\n  reads the "
          "perturbed close J is the one at bar J-2 (flag index J-4). So the\n"
          "  sweep catches the mutant at J if and only if the perturbation "
          "FLIPS that one\n  flag -- asserted as a set equality below, not "
          "argued.")
    mod = load_mutant(*FORWARD_FLAG)
    for frame in sorted(PAIRS):
        close, other = PAIRS[frame]
        hits = set(caught_offsets(mod.ts_peaks_20, close, other))
        base_flags = flags_of(close.to_numpy())
        flipped = set()
        for j in OFFSETS:
            p = close.copy()
            p.iloc[j:] = other.iloc[j:].values
            pf = flags_of(p.to_numpy())
            if bool(base_flags[j - 2 - SUPPORT]) != bool(pf[j - 2 - SUPPORT]):
                flipped.add(j)
        print(f"    {frame}: caught {len(hits)} of {n}; the decisive flag "
              f"(candidate bar J-2) flips at {len(flipped)} offsets")
        print(f"      caught == flag flipped: {hits == flipped} "
              f"(caught {sorted(hits)}, flipped {sorted(flipped)})")
        print(f"      base value of that flag, over the 37 offsets: "
              f"{int(sum(bool(base_flags[j - 2 - SUPPORT]) for j in OFFSETS))}"
              f" of {n} are already peaks")

    print("\n  how sparse the flags are -- that is what makes the sweep "
          "blunt")
    for frame in sorted(PAIRS):
        close, _ = PAIRS[frame]
        f = flags_of(close.to_numpy())
        print(f"    {frame}: peak flags {int(f.sum())} of {f.size} "
              f"({float(f.mean()):.6f})")

    print("\n  offset is a delay, and a negative one is the caller's ask")
    close = walk(400, seed=3)
    base = ts_peaks_20(close)
    for off in (2, -2):
        got = ts_peaks_20(close, offset=off)
        print(f"    offset={off}: equals base.shift({off}): "
              f"{bool(got.equals(base.shift(off).rename(got.name)))}")


def prefix_moved(fn, close, perturbed, j):
    """Did any bar STRICTLY BEFORE j move, value or NaN?"""
    a, b = fn(close).iloc[:j], fn(perturbed).iloc[:j]
    if not (a.isna() == b.isna()).all():
        return True
    m = a.notna()
    return bool((a[m] != b[m]).any())


#: (mutant, how far after the peak the perturbed bar sits, what the mutant
#: illegally reads). For `forward_flag` bar T reads the candidate at T-1,
#: whose own window reaches close T+1, so lifting close p+2 above the peak at
#: bar p flips that flag and moves bar p+1 -- a bar strictly before the
#: perturbation. For `forward_leg` the flag itself reaches p+3.
DESIGNED = [
    ("forward_flag", FORWARD_FLAG, 2, "the candidate one bar too new"),
    ("forward_leg", FORWARD_LEG, 3, "a support leg one bar too far ahead"),
]


def designed():
    head("Gate B -- the designed probe, not a blind sweep")
    print("  The sweep above perturbs a whole tail and asks whether anything "
          "leaked; the\n  peak flag fires on ~14% of candidates, so most "
          "offsets flip nothing and the\n  mutant survives. This probe "
          "instead TARGETS the one close the mutant reads\n  illegally: take "
          "a bar p that IS a peak, lift the close at p + k above it, and\n"
          "  check bar p + k - 1 -- strictly before the perturbation.")
    close = walk()
    base_flags = flags_of(close.to_numpy())
    peaks = [int(f) + SUPPORT for f in np.flatnonzero(base_flags)]
    print(f"  peaks on the walk: {len(peaks)}; the first 50 with room are "
          f"probed")
    big = float(close.max()) * 2.0
    leg_flags = mutant_flags_of(close.to_numpy())
    for name, mutant, k, what in DESIGNED:
        mod = load_mutant(*mutant)
        real_hits, mut_hits, probed, dead = 0, 0, 0, 0
        for p in peaks:
            j = p + k
            if j >= len(close) - 2 or p < LENGTH:
                continue
            probed += 1
            if probed > 50:
                break
            pert = close.copy()
            pert.iloc[j] = big
            if prefix_moved(ts_peaks_20, close, pert, j):
                real_hits += 1
            if prefix_moved(mod.ts_peaks_20, close, pert, j):
                mut_hits += 1
            elif name == "forward_leg" and not leg_flags[p - SUPPORT]:
                dead += 1
        print(f"    {name} ({what}): probed {min(probed, 50)} peaks -- real "
              f"module leaked {real_hits}, mutant caught {mut_hits}")
        if name == "forward_leg":
            print(f"      of the {min(probed, 50) - mut_hits} not caught, "
                  f"{dead} are peaks the MUTANT's own flag already reads as "
                  f"false\n      (it compares p against p+2 and p+3, so a "
                  f"real peak need not be one of its peaks,\n      and then "
                  f"the lift flips nothing)")


def module_flags(c):
    """The module's own flag array, `-1` for a candidate that cannot be
    ordered: the three-valued input the NaN-window test actually runs on."""
    n = c.size
    core = c[SUPPORT:n - SUPPORT]
    ok = np.isfinite(c)
    peak = np.ones(core.size, dtype=bool)
    valid = ok[SUPPORT:n - SUPPORT].copy()
    for i in range(1, SUPPORT + 1):
        peak &= (core > c[SUPPORT - i:n - SUPPORT - i]) & \
            (core > c[SUPPORT + i:n - SUPPORT + i])
        valid &= ok[SUPPORT - i:n - SUPPORT - i] & \
            ok[SUPPORT + i:n - SUPPORT + i]
    return np.where(valid, peak.astype(np.int8), np.int8(-1))


def mutant_flags_of(c):
    """`forward_leg`'s own flag: the support legs ahead are read one bar too
    far (p+2 and p+3 instead of p+1 and p+2)."""
    n = c.size
    core = c[SUPPORT:n - SUPPORT]
    peak = np.ones(core.size, dtype=bool)
    rolled = np.roll(c, -1)
    for i in range(1, SUPPORT + 1):
        peak &= (core > c[SUPPORT - i:n - SUPPORT - i]) & \
            (core > rolled[SUPPORT + i:n - SUPPORT + i])
    return peak


def flags_of(c):
    """The per-candidate peak flag array, flag index j = bar j + SUPPORT."""
    n = c.size
    core = c[SUPPORT:n - SUPPORT]
    peak = np.ones(core.size, dtype=bool)
    for i in range(1, SUPPORT + 1):
        peak &= (core > c[SUPPORT - i:n - SUPPORT - i]) & \
            (core > c[SUPPORT + i:n - SUPPORT + i])
    return peak


# --------------------------------------------------------------- Gates C/D


def gate_c_d():
    head("Gates C/D -- reachability and scale")

    print("\n  x8 / x64 / x1024 -- exact powers of two")
    for frame in sorted(FRAMES):
        close = FRAMES[frame]()
        base = ts_peaks_20(close)
        for k in (8.0, 64.0, 1024.0):
            compare(f"    {frame} x{k:g}", base, ts_peaks_20(close * k))

    print("\n  x10 / x3.7 / x0.1 -- not exact")
    for frame in sorted(FRAMES):
        close = FRAMES[frame]()
        base = ts_peaks_20(close)
        for k in (10.0, 3.7, 0.1):
            compare(f"    {frame} x{k:g}", base, ts_peaks_20(close * k))

    print("\n  non-default lengths under x8")
    close = walk()
    for length in (5, 10, 60, 250):
        compare(f"    length={length}",
                ts_peaks_20(close, length=length),
                ts_peaks_20(close * 8.0, length=length))

    print("\n  ANY strictly increasing transform of price, not only a scale")
    close = walk()
    base = ts_peaks_20(close)
    for name, f in (("log", np.log), ("sqrt", np.sqrt),
                    ("cube", lambda x: x ** 3),
                    ("+1000 (a shift)", lambda x: x + 1000.0)):
        compare(f"    {name}", base, ts_peaks_20(Series(f(close.to_numpy()),
                                                        index=close.index)))
    print("    a DRIFT is not such a transform -- it changes the order "
          "relations:")
    compare("      +0.004 log drift a bar", base,
            ts_peaks_20(Series(close.to_numpy()
                               * np.exp(0.004 * np.arange(len(close))),
                               index=close.index)))
    print("    nor is ROUNDING to a coarser grid (a collapse, not a strictly "
          "increasing map):")
    compare("      the coarse grid vs the same path unrounded",
            ts_peaks_20(coarse_grid()),
            ts_peaks_20(walk(sigma=0.002, seed=55)))
    print("    how many closes a x8 / x1024 scaling collapses onto a "
          "neighbour (0 means the\n    bit-identity above is not luck on "
          "these frames):")
    for frame in sorted(FRAMES):
        c = FRAMES[frame]().to_numpy()
        for k in (8.0, 1024.0, 3.7, 0.1):
            s = c * k
            new_ties = int(((s[1:] == s[:-1]) & (c[1:] != c[:-1])).sum())
            if new_ties:
                print(f"      {frame} x{k:g}: {new_ties} NEW adjacent ties")
        print(f"      {frame}: distinct closes {len(set(c.tolist()))} of "
              f"{c.size}; new adjacent ties under x8/x1024/x3.7/x0.1: "
              f"{[int(((c * k)[1:] == (c * k)[:-1]).sum() - (c[1:] == c[:-1]).sum()) for k in (8.0, 1024.0, 3.7, 0.1)]}")

    print("\n  0 < fires < n, and the value distribution")
    for frame in sorted(FRAMES):
        close = FRAMES[frame]()
        v = ts_peaks_20(close)
        x = v.dropna()
        hist = {int(k): int((x == k).sum()) for k in sorted(x.unique())}
        print(f"    {frame}: fires {len(x)}/{len(close)} "
              f"distinct={x.nunique()} min={x.min():.0f} max={x.max():.0f} "
              f"median={x.median():.1f} mean={x.mean():.4f} hist={hist}")
    for name, close in (("flat", flat(1500)), ("monotone", monotone(1500)),
                        ("falling", falling(1500)), ("zigzag", zigzag(1500))):
        x = ts_peaks_20(close).dropna()
        print(f"    {name}: fires {len(x)}/{len(close)} "
              f"distinct={x.nunique()} values={sorted(x.unique().tolist())}")


# ------------------------------------------------- what the column means


def meaning():
    head("What the column reads")

    print("\n  median and spread by path SHAPE (1,500 bars each)")
    for frame in sorted(FRAMES):
        v = ts_peaks_20(FRAMES[frame]()).dropna()
        print(f"    {frame}: median={v.median():.1f} mean={v.mean():.4f} "
              f"p05={v.quantile(0.05):.1f} p95={v.quantile(0.95):.1f} "
              f"zeros={int((v == 0.0).sum())}/{len(v)}")

    print("\n  one planted outlier, on a walk -- and that its SIZE does not "
          "matter")
    spikes = {}
    for size in (10.0, 50.0, 1000.0):
        close = walk().copy()
        base = ts_peaks_20(close).dropna()
        c = close.to_numpy().copy()
        c[700] = c[700] * (1.0 + size * 0.015)
        hit = ts_peaks_20(Series(c, index=close.index)).dropna()
        spikes[size] = hit
        print(f"    +{size:g} sigma at bar 700: bars moved "
              f"{int((hit != base).sum())}")
    print(f"    +10 sigma and +50 sigma give a bit-identical column: "
          f"{bool(spikes[10.0].equals(spikes[50.0]))}; +10 vs +1000: "
          f"{bool(spikes[10.0].equals(spikes[1000.0]))}")

    print("\n  peaks vs troughs: the same path mirrored")
    close = walk()
    compare("    close vs -close", ts_peaks_20(close),
            variant(close, mirrored=True))

    print("\n  neighbours already in this fork, on the same walk "
          "(a Gate E pre-check, NOT Gate E)")
    import pandas_ta as ta
    close = walk()
    port = ts_peaks_20(close)
    others = {
        "entropy_20": ta.entropy(close, length=20),
        "psl_12": ta.psl(close, length=12),
        "ts_binent_20": ta.ts_binent_20(close),
        "ts_c3_20": ta.ts_c3_20(close),
        "ts_perment_20": ta.ts_perment_20(close),
        "lean_hurst_100": ta.lean_hurst_100(close),
        "chop_14": ta.chop(close, close, close),
        "rsi_14": ta.rsi(close),
    }
    for name, other in others.items():
        if other is None:
            print(f"    {name}: not computable on close alone")
            continue
        s = other if isinstance(other, Series) else other.iloc[:, 0]
        m = port.notna() & s.notna()
        rho = float(port[m].corr(s[m], method="spearman"))
        print(f"    {name}: spearman={rho:.6f} n={int(m.sum())}")


# -------------------------------------------------------------- the guards


def guards():
    head("Guards and edges")

    close = walk(400, seed=3)
    print(f"  insufficient history (19 closes at length 20): "
          f"{ts_peaks_20(close.iloc[:LENGTH - 1])!r}")
    exact = ts_peaks_20(close.iloc[:LENGTH])
    print(f"  exactly 20 closes: fires {int(exact.notna().sum())}, "
          f"first at bar {int(exact.notna().to_numpy().argmax())}, "
          f"value {float(exact.iloc[-1])!r}")
    print(f"  first fired bar on a 400-bar frame: "
          f"{int(ts_peaks_20(close).notna().to_numpy().argmax())}")

    for length in (None, 0, 1, 2, 3, 4, -5, 4.9):
        got = ts_peaks_20(close, length=length)
        print(f"  length={length!r}: name={got.name}")
    for length in (5, 5.9, 21):
        got = ts_peaks_20(close, length=length)
        print(f"  length={length!r}: name={got.name} "
              f"fires={int(got.notna().sum())}")
    five = ts_peaks_20(close, length=5).dropna()
    print(f"  length=5 holds ONE candidate, so the column is 0/1: distinct "
          f"{sorted(five.unique().tolist())}")

    print("\n  a close that is not finite")
    base = ts_peaks_20(close)
    for bad in (np.nan, np.inf, -np.inf):
        c = close.to_numpy().copy()
        c[200] = bad
        v = ts_peaks_20(Series(c, index=close.index))
        emptied = [int(i) for i in np.flatnonzero(v.isna() & base.notna())]
        print(f"    close[200]={bad}: bars emptied {len(emptied)} "
              f"{emptied[:3]}..{emptied[-3:] if emptied else []}")
    print("  `length` bars is the INTERIOR rule; nearer either end the "
          "warm-up or the end of\n  the frame swallows part of the span, so "
          "fewer bars are emptied:")
    for at in (0, 2, 5, 19, 21, 200, len(close) - 21, len(close) - 20,
               len(close) - 3, len(close) - 1):
        c = close.to_numpy().copy()
        c[at] = np.nan
        v = ts_peaks_20(Series(c, index=close.index))
        emptied = [int(i) for i in np.flatnonzero(v.isna() & base.notna())]
        print(f"    close[{at}]=nan: bars emptied {len(emptied)} "
              f"{emptied[:2]}..{emptied[-2:] if emptied else []}")
    print("  a non-positive or subnormal close is NOT rejected -- the column "
          "takes no\n  ratio, so it still compares:")
    for bad in (0.0, -5.0, 1e-310):
        c = close.to_numpy().copy()
        c[200] = bad
        v = ts_peaks_20(Series(c, index=close.index))
        print(f"    close[200]={bad!r}: fires {int(v.notna().sum())} of "
              f"{len(close)}, bar 200 = {float(v.iloc[200])!r}")

    print("\n  fillna, and distinct names")
    print(f"    fillna=0 leaves "
          f"{int(ts_peaks_20(close, fillna=0).isna().sum())} NaNs")
    for length in (20, 40):
        print(f"    length={length}: {ts_peaks_20(close, length=length).name}")

    print("\n  the accessor and the registration")
    import pandas as pd
    import pandas_ta as ta
    df = pd.DataFrame({"close": close.to_numpy()})
    acc = df.ta.ts_peaks_20()
    print(f"    df.ta.ts_peaks_20() -> {acc.name}, equals the function: "
          f"{bool(acc.equals(ts_peaks_20(df['close'])))}")
    print(f"    df.ta.ts_peaks_20(length=40) -> "
          f"{df.ta.ts_peaks_20(length=40).name}")
    print(f"    in Category['statistics']: "
          f"{'ts_peaks_20' in ta.Category['statistics']}")


# ---------------------------------------------------------------- the cost


def cost():
    head("Cost")
    for n in (10000, 100000, 400000):
        close = walk(n, seed=12)
        best = min(_timed(close) for _ in range(3))
        tracemalloc.start()
        ts_peaks_20(close)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(f"  n={n}: best of three {best * 1000:.0f} ms, traced peak "
              f"{peak / 1e6:.1f} MB; the int8 flag array is "
              f"{(n - 2 * SUPPORT) / 1e6:.1f} MB and one int64 row-sum pass "
              f"over {(n - LENGTH + 1)} windows x {CANDIDATES} candidates")

    print("\n  peak memory against `length`, which is a caller parameter: "
          "the row reductions\n  must not materialise a (rows, candidates) "
          "temporary, or the peak grows with it")
    close = walk(400000, seed=12)
    for length in (20, 60, 250):
        best = min(_timed(close, length) for _ in range(3))
        tracemalloc.start()
        ts_peaks_20(close, length=length)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(f"    n=400000 length={length}: best of three "
              f"{best * 1000:.0f} ms, traced peak {peak / 1e6:.1f} MB; a "
              f"(rows, candidates) bool array would be "
              f"{(400000 - length + 1) * (length - 2 * SUPPORT) / 1e6:.1f} MB")

    print("\n  the two spellings of the NaN-window test, measured on the same "
          "windows.\n  The flag array is the MODULE's own, over a frame with a "
          "NaN and a -inf planted,\n  so all three reachable values (-1, 0, 1) "
          "are present -- a comparison run on an\n  all-zero array could not "
          "have caught a difference:")
    c = close.to_numpy(dtype=float).copy()
    c[1000], c[2000] = np.nan, -np.inf
    flags = module_flags(c)
    counts = np.bincount(flags.astype(np.int64) + 1, minlength=3)
    print(f"    flag values present: -1 x {int(counts[0])}, "
          f"0 x {int(counts[1])}, 1 x {int(counts[2])} "
          f"(of {flags.size} candidates)")
    # `module_flags` is a retyped copy of the module's lines, so it is checked
    # against the module itself rather than trusted: the same windows, summed
    # and masked the same way, must reproduce the shipped column exactly.
    w = sliding_window_view(flags, CANDIDATES)
    expect = np.where(w.min(axis=1) < 0, np.nan,
                      w.sum(axis=1, dtype=np.int64))
    got = ts_peaks_20(Series(c)).to_numpy()[LENGTH - 1:]
    print(f"    the retyped flags reproduce the shipped column on all "
          f"{expect.size} bars: {bool(np.array_equal(expect, got, equal_nan=True))}")
    for length in (20, 250):
        windows = sliding_window_view(flags, length - 2 * SUPPORT)
        peaks = {}
        for name, fn in (("(windows < 0).any(axis=1)",
                          lambda w: (w < 0).any(axis=1)),
                         ("windows.min(axis=1) < 0",
                          lambda w: w.min(axis=1) < 0)):
            tracemalloc.start()
            out = fn(windows)
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            peaks[name] = (peak, out)
            print(f"    length={length}: {name} traced peak "
                  f"{peak / 1e6:.1f} MB")
        a, b = (v[1] for v in peaks.values())
        print(f"    length={length}: the two agree on every window: "
              f"{bool(np.array_equal(a, b))}")


def _timed(close, length=None):
    t0 = time.perf_counter()
    ts_peaks_20(close, length=length)
    return time.perf_counter() - t0


SECTIONS = {
    "source": source,
    "gate_a": gate_a,
    "gate_b": gate_b,
    "designed": designed,
    "gate_c_d": gate_c_d,
    "meaning": meaning,
    "guards": guards,
    "cost": cost,
}


if __name__ == "__main__":
    wanted = sys.argv[1:] or list(SECTIONS)
    for key in wanted:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r}; "
                             f"one of {list(SECTIONS)}")
        SECTIONS[key]()
