# -*- coding: utf-8 -*-
"""Reproduce every number in docs/TsPerment20Measured.md for `ts_perment_20`
(PandasTa issue #91, TS-PERMENT-20).

Run from the repository root:

    python docs/measure_ts_perment_20.py            # every section
    python docs/measure_ts_perment_20.py gate_a     # one section

Gates A-D and the synthetic reachability only. Gate E needs the private
Backtesting engine and the 89 frozen ALTPORT-1 BIST frames, which are not in
this worktree; the launcher runs it after the porting session.
"""
import importlib
import itertools
import math
import sys
import time
import tracemalloc
import types

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.statistics.ts_perment_20 import ts_perment_20

LENGTH = 20
DIMENSION = 3
TRIPLES = LENGTH - (DIMENSION - 1)  # 18
REAL = importlib.import_module("pandas_ta.statistics.ts_perment_20")
PATTERNS = REAL.PATTERNS


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
    """Two-decimal prices: consecutive closes TIE often, which is the regime
    the tie rule decides."""
    return Series(np.round(walk(n, seed).to_numpy(), 2))


def coarse_grid(n=1500, seed=55, sigma=0.002, decimals=1):
    """A quiet path on a COARSE price grid: consecutive closes tie on a large
    share of bars, which is where the tie rule earns or loses its keep."""
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
    """An AR(1) on the returns with NEGATIVE phi: up follows down, so the
    triples concentrate on the two zigzag patterns."""
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
          f"bit-equal={bit}/{int(m.sum())} "
          f"bars|diff|>1e-12={int((diff > 1e-12).sum())} spearman={rho_text} "
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


def rank_vector(triple):
    """The ordinal pattern as tsfresh spells it: `argsort(argsort(x))`, which
    breaks ties by index because numpy's 3-element sort is stable."""
    arr = np.asarray(triple, dtype=float)
    return tuple(int(v) for v in np.argsort(np.argsort(arr)))


def module_code(triple):
    a, b, z = (float(v) for v in triple)
    return 4 * int(a <= b) + 2 * int(b <= z) + int(a <= z)


def source():
    head("The source formula, and the encoding")
    print(f"  tsfresh in this worktree: {tsfresh_installed()}")

    print("\n  Every order type of three points, exhaustively (all 27 triples")
    print("  of values drawn from {1, 2, 3} with repetition -- every weak")
    print("  order on 3 elements appears among them):")
    code_to_ranks, seen = {}, {}
    for triple in itertools.product((1.0, 2.0, 3.0), repeat=3):
        k, rv = module_code(triple), rank_vector(triple)
        code_to_ranks.setdefault(k, set()).add(rv)
        seen.setdefault(k, []).append(triple)
    for k in sorted(code_to_ranks):
        print(f"    code {k}: argsort rank vectors {sorted(code_to_ranks[k])}"
              f"  ({len(seen[k])} of the 27 triples)")
    print(f"  codes observed      : {sorted(code_to_ranks)}")
    print(f"  codes never observed: "
          f"{sorted(set(range(8)) - set(code_to_ranks))}")
    print(f"  the module's PATTERNS: {list(REAL.PATTERNS)}")
    print(f"  one rank vector per code: "
          f"{all(len(v) == 1 for v in code_to_ranks.values())}")
    print("\n  The screen prototype's loop, for contrast:")
    print("    for k in (0, 1, 3, 4, 6, 7)  -- `docs/issues/screen/"
          "ind_screen.py`")
    proto_loop = (0, 1, 3, 4, 6, 7)
    print(f"    realisable codes it SKIPS   : "
          f"{sorted(set(code_to_ranks) - set(proto_loop))}")
    print(f"    unrealisable codes it visits: "
          f"{sorted(set(proto_loop) - set(code_to_ranks))}")
    w = walk()
    codes = codes_of(w.to_numpy())
    share = {k: float(np.mean(codes == k)) for k in sorted(set(code_to_ranks))}
    print(f"    share of a walk's triples in the skipped codes 2 and 5: "
          f"{share[2] + share[5]:.6f}")
    print(f"    per-code shares on a 1,500-bar walk: "
          f"{ {k: round(v, 6) for k, v in share.items()} }")


def codes_of(c):
    a, b, z = c[:-2], c[1:-1], c[2:]
    return (4 * (a <= b) + 2 * (b <= z) + (a <= z)).astype(int)


# ----------------------------------------------------------------- Gate A


def entropy_of_counts(counts, triples=TRIPLES):
    """The module's accumulation order: pattern by pattern, in PATTERNS
    order."""
    h = 0.0
    for n in counts:
        if n:
            p = n / triples
            h -= p * math.log(p)
    return h


def argsort_definition(close, length=LENGTH):
    """tsfresh's `permutation_entropy` spelled window by window with numpy's
    own `argsort` and `np.unique`, sharing no code with the module:

        X = subchunks of `dimension` consecutive closes, tau = 1
        permutations = argsort(argsort(X))
        _, counts = unique(permutations, axis=0, return_counts=True)
        probs = counts / len(permutations)
        return -sum(probs * log(probs))
    """
    c = close.to_numpy(dtype=float)
    out = np.full(c.size, np.nan)
    for t in range(length - 1, c.size):
        w = c[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        x = sliding_window_view(w, DIMENSION)
        perms = np.argsort(np.argsort(x, axis=1), axis=1)
        _, counts = np.unique(perms, axis=0, return_counts=True)
        probs = counts / len(perms)
        out[t] = float(-np.sum(probs * np.log(probs)))
    return Series(out, index=close.index)


def scalar_loop(close, length=LENGTH):
    """An independent per-window loop in plain Python scalars: the pattern is
    the tuple of sorted positions, ties broken by index through `sorted` on
    `(value, position)`."""
    c = [float(v) for v in close.to_numpy(dtype=float)]
    out = [float("nan")] * len(c)
    for t in range(length - 1, len(c)):
        w = c[t - length + 1:t + 1]
        if any(math.isnan(v) or math.isinf(v) for v in w):
            continue
        counts = {}
        for i in range(len(w) - 2):
            tri = w[i:i + 3]
            order = tuple(p for _, p in sorted((v, p)
                                               for p, v in enumerate(tri)))
            counts[order] = counts.get(order, 0) + 1
        n = len(w) - 2
        h = 0.0
        for v in counts.values():
            p = v / n
            h -= p * math.log(p)
        out[t] = h
    return Series(out, index=close.index)


def screen_candidate():
    """`REG["ts_perment_20"]["fn"]` out of the screen's own registry, when
    this worktree has `docs/issues/` (gitignored, so a clone does not)."""
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
    return mod.REG["ts_perment_20"]["fn"]


def prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py` candidate `ts_perment_20`, retyped
    verbatim because that tree is gitignored:

        def perm_entropy3(x, n):
            a, b, c = x.shift(2), x.shift(1), x
            pid = (4*(a < b) + 2*(b < c) + 1*(a < c)).where(a.notna() & c.notna())
            h = pd.Series(0.0, index=x.index)
            for k in (0, 1, 3, 4, 6, 7):
                p = (pid == k).astype(float).rolling(n - 2).mean()
                h -= np.where(p > 0, p * np.log(p.where(p > 0, 1)), 0)
            return (h / np.log(6)).where(pid.rolling(n - 2).count() == n - 2)

        @cand("ts_perment_20", ...)
        def _(o, h, l, c, v): return perm_entropy3(c, 20)
    """
    x = close
    a, b, z = x.shift(2), x.shift(1), x
    pid = (4 * (a < b) + 2 * (b < z) + 1 * (a < z)).where(a.notna()
                                                          & z.notna())
    h = Series(0.0, index=x.index)
    for k in (0, 1, 3, 4, 6, 7):
        p = (pid == k).astype(float).rolling(length - 2).mean()
        h -= np.where(p > 0, p * np.log(p.where(p > 0, 1)), 0)
    return (h / np.log(6)).where(pid.rolling(length - 2).count() == length - 2)


def variant(close, length=LENGTH, patterns=PATTERNS, normalise=False,
            strict=False, on_returns=False, triples_window=False,
            flat_is_nan=False):
    """The module's arithmetic with one reading changed, so the cost of each
    decision is a measurement rather than an argument."""
    c = close.to_numpy(dtype=float)
    if on_returns:
        r = np.full(c.size, np.nan)
        r[1:] = c[1:] / c[:-1] - 1.0
        c = r
    ok = np.isfinite(c)
    a, b, z = c[:-2], c[1:-1], c[2:]
    with np.errstate(invalid="ignore"):
        if strict:
            code = (4 * (a < b) + 2 * (b < z) + (a < z)).astype(np.int8)
        else:
            code = (4 * (a <= b) + 2 * (b <= z) + (a <= z)).astype(np.int8)
    codes = np.where(ok[:-2] & ok[1:-1] & ok[2:], code, -1)
    triples = length if triples_window else length - 2
    if codes.size < triples:
        return Series(np.full(c.size, np.nan), index=close.index)
    windows = sliding_window_view(codes, triples)
    h = np.zeros(windows.shape[0])
    for k in patterns:
        p = (windows == k).sum(axis=1) / triples
        h -= np.where(p > 0, p * np.log(np.where(p > 0, p, 1.0)), 0.0)
    if normalise:
        h = h / math.log(len(patterns))
    bad = (windows < 0).any(axis=1)
    if flat_is_nan:
        bad = bad | (h == 0.0)
    out = np.full(c.size, np.nan)
    # Row i's newest triple ends at bar i + triples + 1.
    out[triples + 1:] = np.where(bad, np.nan, h)
    return Series(out, index=close.index)


def even_split_witness(tries=200000, seed=2026):
    """A 20-close window whose 18 triples hit each of the six patterns exactly
    three times -- the ceiling log 6. Searched, then printed so the test can
    pin it as a constant."""
    rng = np.random.default_rng(seed)
    base = np.arange(1.0, LENGTH + 1.0)
    for i in range(tries):
        w = rng.permutation(base)
        codes = codes_of(w)
        counts = [int((codes == k).sum()) for k in PATTERNS]
        if counts == [3] * 6:
            return w, i
    return None, tries


def gate_a():
    head("Gate A -- correctness")

    print("\nA1. Hand-derived windows, exact closed form vs the module")
    w, tries = even_split_witness()
    top = entropy_of_counts([3] * 6)
    print(f"  even-split witness found after {tries} shuffles: "
          f"{[int(v) for v in w]}")
    print(f"  its pattern counts: "
          f"{[int((codes_of(w) == k).sum()) for k in PATTERNS]}")
    cases = [
        ("20 strictly rising closes (every triple pattern 7)",
         Series(100.0 + 0.5 * np.arange(LENGTH)), LENGTH, [18],
         ("0", 0.0)),
        ("20 identical closes (ties read as rising: pattern 7)",
         Series(np.full(LENGTH, 100.0)), LENGTH, [18], ("0", 0.0)),
        ("20 strictly falling closes (every triple pattern 0)",
         Series(100.0 - 0.5 * np.arange(LENGTH)), LENGTH, [18],
         ("0", 0.0)),
        ("zigzag 100/101 x 20 (nine of pattern 5, nine of pattern 3)",
         zigzag(LENGTH), LENGTH, [9, 9], ("log 2", math.log(2.0))),
        ("the even-split witness (three of each of the six)",
         Series(w), LENGTH, [3] * 6, ("log 6", math.log(6.0))),
        ("length 4: closes [1,3,2,4] -> patterns (5, 3), one each",
         Series([1.0, 3.0, 2.0, 4.0]), 4, [1, 1], ("log 2", math.log(2.0))),
        ("length 5: closes [1,3,2,4,5] -> patterns (7, 5, 3), one each",
         Series([1.0, 3.0, 2.0, 4.0, 5.0]), 5, [1, 1, 1],
         ("log 3", math.log(3.0))),
    ]
    for name, close, length, counts, (form, closed) in cases:
        got = ts_perment_20(close, length=length)
        v = float(got.iloc[length - 1])
        acc = entropy_of_counts(counts, length - 2)
        print(f"  {name}\n    accumulated={acc!r} module={v!r} "
              f"diff={abs(v - acc):.3e} name={got.name}")
        print(f"    closed form {form}={closed!r}, ulps from the "
              f"accumulation: "
              f"{round((acc - closed) / np.spacing(closed)) if closed else 0}")
    print(f"  log 6 = {math.log(6.0)!r}; the module's accumulation of six "
          f"3/18 terms = {top!r}")
    print(f"  ulps between them: "
          f"{round((top - math.log(6.0)) / np.spacing(math.log(6.0)))}")

    print("\nA2. The screen prototype (retyped, and imported from the "
          "owner's tree)")
    for frame in ("walk", "tick-rounded", "coarse-grid"):
        close = FRAMES[frame]()
        port = ts_perment_20(close)
        proto = prototype(close)
        print(f"  {frame}:")
        compare("    port vs the prototype retyped", port, proto)
        compare("    port/log 6 vs the prototype retyped",
                port / math.log(6.0), proto)
        fn = screen_candidate()
        if fn is None:
            print("    the screen registry is absent from this worktree")
        else:
            imported = fn(close, close, close, close, close)
            compare("    the retyped prototype vs the IMPORTED candidate",
                    proto, Series(np.asarray(imported, dtype=float),
                                  index=close.index))
            compare("    port/log 6 vs the IMPORTED candidate",
                    port / math.log(6.0),
                    Series(np.asarray(imported, dtype=float),
                           index=close.index))
    print("  the prototype's loop drops the realisable patterns 2 and 5 and "
          "visits the\n  unrealisable 1 and 6, so it is a FOUR-pattern sum "
          "(see the `source` section)")

    print("\nA3. tsfresh's own spelling: argsort(argsort(x)) + np.unique, "
          "window by window")
    for frame in ("walk", "tick-rounded", "coarse-grid", "two-point"):
        close = FRAMES[frame](n=600)
        compare(f"  {frame}", ts_perment_20(close),
                argsort_definition(close))

    print("\n  what a PURE reordering of the six terms costs (same counts, "
          "same np.log,\n  only PATTERNS in code order instead of rank-vector "
          "order):")
    for frame in ("walk", "tick-rounded", "coarse-grid", "two-point"):
        close = FRAMES[frame](n=600)
        compare(f"    {frame}", ts_perment_20(close),
                variant(close, patterns=(0, 2, 3, 4, 5, 7)))

    print("\nA4. An independent plain-Python scalar loop")
    for frame in ("walk", "tick-rounded", "coarse-grid"):
        close = FRAMES[frame](n=600)
        compare(f"  {frame}", ts_perment_20(close), scalar_loop(close))

    print("\nA5. The open readings, priced on a walk, a tick-rounded walk "
          "and a coarse grid")
    for frame in ("walk", "tick-rounded", "coarse-grid"):
        close = FRAMES[frame]()
        port = ts_perment_20(close)
        print(f"  {frame}:")
        compare("    SIX realisable patterns. Rejected: the prototype's four "
                "(0,1,3,4,6,7)",
                port, variant(close, patterns=(0, 1, 3, 4, 6, 7)))
        compare("    nats, UNNORMALISED. Rejected: dividing by log 6",
                port, variant(close, normalise=True))
        compare("    ties broken by INDEX (<=). Rejected: strict < "
                "(the prototype's folding)",
                port, variant(close, strict=True))
        compare("    the window is 20 CLOSES (18 triples). Rejected: 20 "
                "triples (22 closes)",
                port, variant(close, triples_window=True))
        compare("    the input is CLOSES. Rejected: the 19 returns of the "
                "same 20 closes",
                port, variant(close, on_returns=True))
    print("  tie rate (share of triples with at least one tied pair):")
    for frame in sorted(FRAMES):
        c = FRAMES[frame]().to_numpy()
        a, b, z = c[:-2], c[1:-1], c[2:]
        tied = (a == b) | (b == z) | (a == z)
        print(f"    {frame}: {float(tied.mean()):.6f} "
              f"({int(tied.sum())} of {tied.size} triples)")

    print("\nA6. The degenerate window: 0.0, not NaN -- and what that costs")
    for name, close in (("flat 300 closes", flat()),
                        ("monotone 300 closes", monotone()),
                        ("1,500-bar walk", walk())):
        port = ts_perment_20(close)
        nan_reading = variant(close, flat_is_nan=True)
        fired = int(port.notna().sum())
        zeros = int((port == 0.0).sum())
        print(f"  {name}: fires {fired}/{len(close)}, of those exactly 0.0: "
              f"{zeros}; the NaN reading fires "
              f"{int(nan_reading.notna().sum())}/{len(close)}")
    print("  a flat window and a strictly rising one BOTH read 0.0 -- the "
          "column reads\n  the ORDER, and a tie reads as a rise:")
    print(f"    flat    first value: "
          f"{float(ts_perment_20(flat()).iloc[LENGTH - 1])!r}")
    print(f"    rising  first value: "
          f"{float(ts_perment_20(monotone()).iloc[LENGTH - 1])!r}")


# ----------------------------------------------------------------- Gate B


BACK_DATE_TWO = (
    "    out[length - 1:] = np.where(bad, np.nan, h)",
    "    out[length - 3:c.size - 2] = np.where(bad, np.nan, h)")
BACK_DATE_FULL = (
    "    out[length - 1:] = np.where(bad, np.nan, h)",
    "    out[:windows.shape[0]] = np.where(bad, np.nan, h)")
FORWARD_LEG = (
    "    a, b, z = c[:-LEGS], c[TAU:c.size - TAU], c[LEGS:]",
    "    a, b, z = c[:-LEGS], c[TAU:c.size - TAU], np.roll(c, -1)[LEGS:]")
ROLLED_WINDOW = (
    "    windows = sliding_window_view(codes, triples)",
    "    windows = sliding_window_view(np.roll(codes, -(length // 2)), "
    "triples)")
FORWARD_TRIPLE = (
    "    windows = sliding_window_view(codes, triples)",
    "    windows = sliding_window_view(np.roll(codes, -1), triples)")

MUTANTS = [BACK_DATE_TWO, BACK_DATE_FULL, FORWARD_LEG, ROLLED_WINDOW,
           FORWARD_TRIPLE]
MUTANT_IDS = ["back_date_two", "back_date_full", "forward_leg",
              "rolled_window", "forward_triple"]
OFFSETS = range(40, 1500, 40)
PAIRS = {
    "walk": (walk(), walk(seed=97)),
    "tick-rounded": (tick_rounded(), tick_rounded(seed=56)),
    "heavy-tailed": (heavy_tailed(), heavy_tailed(seed=8)),
}


def load_mutant(old, new):
    src = open(REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_perment_20_mutant")
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
              f"{len(caught_offsets(ts_perment_20, close, other))}/{n}")
    for i, (old, new) in enumerate(MUTANTS):
        mod = load_mutant(old, new)
        for frame in sorted(PAIRS):
            close, other = PAIRS[frame]
            live = not mod.ts_perment_20(close).equals(ts_perment_20(close))
            hits = caught_offsets(mod.ts_perment_20, close, other)
            print(f"    {MUTANT_IDS[i]}, {frame}: {len(hits)}/{n} "
                  f"missed={[j for j in OFFSETS if j not in set(hits)]} "
                  f"live-mutation={live}")

    print("\n  the same five mutants at non-default lengths, on the walk")
    close, other = PAIRS["walk"]
    for length in (10, 60, 4):
        def real(c, length=length):
            return ts_perment_20(c, length=length)
        first = int(real(close).notna().to_numpy().argmax())
        print(f"    length={length}: real module "
              f"{len(caught_offsets(real, close, other))}/{n}, first value "
              f"at bar {first}")
        for i, (old, new) in enumerate(MUTANTS):
            mod = load_mutant(old, new)

            def mutated(c, mod=mod, length=length):
                return mod.ts_perment_20(c, length=length)
            hits = caught_offsets(mutated, close, other)
            live = not mutated(close).equals(real(close))
            print(f"      {MUTANT_IDS[i]}: {len(hits)}/{n} "
                  f"missed={[j for j in OFFSETS if j not in set(hits)]} "
                  f"live-mutation={live}")

    print("\n  WHY a one-bar leak is missed at an offset, measured exactly.")
    print("  The `forward_triple` mutant writes bar T from a window that "
          "ends one triple\n  late, so at offset J the only prefix bar that "
          "can move is J-1, and it moves\n  only if the perturbation changes "
          "the CODE of the triple ending at bar J, or\n  changes the window's "
          "count vector to something with a different entropy.")
    mod = load_mutant(*FORWARD_TRIPLE)
    for frame in sorted(PAIRS):
        close, other = PAIRS[frame]
        miss = missed(mod.ts_perment_20, close, other)
        base_codes = codes_of(close.to_numpy())
        same_code, absorbed = [], []
        for j in OFFSETS:
            p = close.copy()
            p.iloc[j:] = other.iloc[j:].values
            pc = codes_of(p.to_numpy())
            if base_codes[j - 2] == pc[j - 2]:
                same_code.append(j)
                continue
            if j not in set(miss):
                continue
            # the mutant's window at bar J-1 holds the triples ending at bars
            # J-TRIPLES+2 .. J, i.e. code indices J-1-TRIPLES .. J-2.
            lo = j - 1 - TRIPLES
            cb = [int((base_codes[lo:j - 1] == k).sum()) for k in PATTERNS]
            cp = [int((pc[lo:j - 1] == k).sum()) for k in PATTERNS]
            absorbed.append((j, cb, cp, sorted(cb) == sorted(cp)))
        print(f"    {frame}: missed {len(miss)} of 37 -- at "
              f"{len([j for j in miss if j in set(same_code)])} the triple's "
              f"code is UNCHANGED, so the mutant's window is identical and "
              f"there is nothing to detect")
        print(f"      code unchanged at {len(same_code)} offsets, all of them "
              f"missed: {set(same_code) <= set(miss)}")
        print(f"      the other {len(absorbed)} missed offsets changed the "
              f"code and the column ABSORBED it:")
        for j, cb, cp, perm in absorbed:
            print(f"        J={j}: counts {cb} -> {cp}, a permutation: "
                  f"{perm}")

    print("\n  how sensitive the sweep is: consecutive windows that share "
          "their pattern counts")
    for frame in sorted(PAIRS):
        close, _ = PAIRS[frame]
        codes = codes_of(close.to_numpy())
        w = sliding_window_view(codes, TRIPLES)
        counts = np.stack([(w == k).sum(axis=1) for k in PATTERNS], axis=1)
        same = int((counts[:-1] == counts[1:]).all(axis=1).sum())
        print(f"    {frame}: {same} of {counts.shape[0] - 1} consecutive "
              f"window pairs have identical counts")

    print("\n  offset is a delay, and a negative one is the caller's ask")
    close = walk(400, seed=3)
    base = ts_perment_20(close)
    for off in (2, -2):
        got = ts_perment_20(close, offset=off)
        print(f"    offset={off}: equals base.shift({off}): "
              f"{bool(got.equals(base.shift(off).rename(got.name)))}")


# --------------------------------------------------------------- Gates C/D


def gate_c_d():
    head("Gates C/D -- reachability and scale")

    print("\n  x8 / x64 / x1024 -- exact powers of two")
    for frame in sorted(FRAMES):
        close = FRAMES[frame]()
        base = ts_perment_20(close)
        for k in (8.0, 64.0, 1024.0):
            compare(f"    {frame} x{k:g}", base, ts_perment_20(close * k))

    print("\n  x10 / x3.7 / x0.1 -- not exact, and the rounding is monotone")
    for frame in sorted(FRAMES):
        close = FRAMES[frame]()
        base = ts_perment_20(close)
        for k in (10.0, 3.7, 0.1):
            compare(f"    {frame} x{k:g}", base, ts_perment_20(close * k))

    print("\n  non-default lengths under x8")
    close = walk()
    for length in (4, 10, 60, 250):
        compare(f"    length={length}",
                ts_perment_20(close, length=length),
                ts_perment_20(close * 8.0, length=length))

    print("\n  ANY strictly increasing transform of price, not only a scale")
    close = walk()
    base = ts_perment_20(close)
    for name, f in (("log", np.log), ("sqrt", np.sqrt),
                    ("cube", lambda x: x ** 3),
                    ("+1000 (a shift)", lambda x: x + 1000.0)):
        compare(f"    {name}", base, ts_perment_20(Series(f(close.to_numpy()),
                                                          index=close.index)))
    print("    a DRIFT is not such a transform -- it changes the order "
          "relations:")
    compare("      +0.004 log drift a bar", base,
            ts_perment_20(Series(close.to_numpy()
                                 * np.exp(0.004 * np.arange(len(close))),
                                 index=close.index)))

    print("\n  0 < fires < n, and how much it varies")
    for frame in sorted(FRAMES):
        close = FRAMES[frame]()
        v = ts_perment_20(close)
        x = v.dropna()
        print(f"    {frame}: fires {len(x)}/{len(close)} "
              f"distinct={x.nunique()} (at 1e-12: "
              f"{x.round(12).nunique()}) "
              f"min={x.min():.6f} max={x.max():.6f} median={x.median():.6f} "
              f"zeros={int((x == 0.0).sum())} at-the-ceiling="
              f"{int((x >= entropy_of_counts([3] * 6)).sum())}")


# ---------------------------------------------------- the attainable values


def satisfying_count_vectors(triples):
    """Count vectors reachable under the ONE constraint that consecutive
    triples share a comparison: bit B of code[t] is bit A of code[t+1]. This
    is NECESSARY; whether it is also sufficient is measured at length 6
    below."""
    states = {}
    for k in PATTERNS:
        key = ((k >> 1) & 1,
               tuple(1 if p == k else 0 for p in PATTERNS))
        states[key] = True
    for _ in range(triples - 1):
        nxt = {}
        for (bit, counts) in states:
            for k in PATTERNS:
                if ((k >> 2) & 1) != bit:
                    continue
                c = list(counts)
                c[PATTERNS.index(k)] += 1
                nxt[(((k >> 1) & 1), tuple(c))] = True
        states = nxt
    return {counts for _, counts in states}


def realised_count_vectors(length, limit=None):
    """Exhaustive over all orderings of `length` DISTINCT closes."""
    out = set()
    for perm in itertools.islice(
            itertools.permutations(range(1, length + 1)), limit):
        codes = codes_of(np.asarray(perm, dtype=float))
        out.add(tuple(int((codes == k).sum()) for k in PATTERNS))
    return out


def attainable():
    head("The attainable values")

    print("\n  length 6 (four triples): exhaustive over all 720 orderings of "
          "six distinct closes")
    realised = realised_count_vectors(6)
    satisfying = satisfying_count_vectors(4)
    print(f"    count vectors realised by a permutation: {len(realised)}")
    print(f"    count vectors satisfying the shared-comparison constraint: "
          f"{len(satisfying)}")
    print(f"    the two sets are equal: {realised == satisfying}")
    print(f"    satisfying but not realised: "
          f"{sorted(satisfying - realised)}")
    vals = sorted({round(entropy_of_counts(c, 4), 12) for c in realised})
    print(f"    distinct values at length 6, to 1e-12: {len(vals)}: {vals}")

    print("\n  length 7 (five triples): exhaustive over all 5,040 orderings")
    realised7 = realised_count_vectors(7)
    satisfying7 = satisfying_count_vectors(5)
    print(f"    realised {len(realised7)}, satisfying {len(satisfying7)}, "
          f"equal: {realised7 == satisfying7}")

    print("\n  length 20 (eighteen triples)")
    satisfying20 = satisfying_count_vectors(TRIPLES)
    print(f"    count vectors satisfying the constraint: {len(satisfying20)}")
    vals20 = {round(entropy_of_counts(c), 12) for c in satisfying20}
    print(f"    distinct values over them, to 1e-12: {len(vals20)}")
    print(f"    range: {min(vals20):.6f} .. {max(vals20):.6f}")
    rng = np.random.default_rng(5)
    base = np.arange(1.0, LENGTH + 1.0)
    seen = set()
    for _ in range(200000):
        codes = codes_of(rng.permutation(base))
        seen.add(tuple(int((codes == k).sum()) for k in PATTERNS))
    print(f"    of those, reached by 200,000 random orderings of 20 distinct "
          f"closes: {len(seen)}")
    print(f"    all of them satisfy the constraint: "
          f"{seen <= satisfying20}")
    print(f"    the even split (3,3,3,3,3,3) is among them: "
          f"{(3,) * 6 in seen}")


# ------------------------------------------------- what the column means


def meaning():
    head("What the column reads")

    print("\n  median of the column by path SHAPE (1,500 bars each)")
    for frame in sorted(FRAMES):
        v = ts_perment_20(FRAMES[frame]()).dropna()
        print(f"    {frame}: median={v.median():.6f} "
              f"p05={v.quantile(0.05):.6f} p95={v.quantile(0.95):.6f}")
    for name, close in (("flat", flat(1500)), ("monotone", monotone(1500)),
                        ("zigzag", zigzag(1500))):
        v = ts_perment_20(close).dropna()
        print(f"    {name}: median={v.median():.6f} "
              f"distinct={v.nunique()}")

    print("\n  one planted outlier, on a walk -- and that its SIZE does not "
          "matter")
    spikes = {}
    for size in (10.0, 50.0, 1000.0):
        close = walk().copy()
        base = ts_perment_20(close).dropna()
        c = close.to_numpy().copy()
        c[700] = c[700] * (1.0 + size * 0.015)
        hit = ts_perment_20(Series(c, index=close.index)).dropna()
        spikes[size] = hit
        moved = int((hit != base).sum())
        print(f"    +{size:g} sigma at bar 700: bars moved {moved}, "
              f"median over them "
              f"{hit[hit != base].median():.6f} against the frame's "
              f"{base.median():.6f}")
    print(f"    +10 sigma and +50 sigma give a bit-identical column: "
          f"{bool(spikes[10.0].equals(spikes[50.0]))}; +10 vs +1000: "
          f"{bool(spikes[10.0].equals(spikes[1000.0]))}")

    print("\n  the coarse grid against the same path unrounded "
          "(46% of triples tie)")
    compare("    coarse grid vs unrounded",
            ts_perment_20(coarse_grid()),
            ts_perment_20(walk(sigma=0.002, seed=55)))

    print("\n  the tie rule's reach: the column on a tick grid vs the same "
          "path unrounded")
    close = walk()
    compare("    walk vs its 2-decimal rounding", ts_perment_20(close),
            ts_perment_20(Series(np.round(close.to_numpy(), 2),
                                 index=close.index)))

    print("\n  neighbours already in this fork, on the same walk "
          "(a Gate E pre-check, NOT Gate E)")
    import pandas_ta as ta
    close = walk()
    port = ts_perment_20(close)
    others = {
        "entropy_20": ta.entropy(close, length=20),
        "psl_12": ta.psl(close, length=12),
        "ts_binent_20": ta.ts_binent_20(close),
        "ts_c3_20": ta.ts_c3_20(close),
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
          f"{ts_perment_20(close.iloc[:LENGTH - 1])!r}")
    exact = ts_perment_20(close.iloc[:LENGTH])
    print(f"  exactly 20 closes: fires {int(exact.notna().sum())}, "
          f"first at bar {int(exact.notna().to_numpy().argmax())}, "
          f"value {float(exact.iloc[-1])!r}")
    print(f"  first fired bar on a 400-bar frame: "
          f"{int(ts_perment_20(close).notna().to_numpy().argmax())}")

    for length in (None, 0, 1, 2, 3, -5, 3.9):
        got = ts_perment_20(close, length=length)
        print(f"  length={length!r}: name={got.name}")
    for length in (4, 4.9, 21):
        got = ts_perment_20(close, length=length)
        print(f"  length={length!r}: name={got.name} "
              f"fires={int(got.notna().sum())}")
    print(f"  length=4 is the smallest that can vary: a ONE-triple window "
          f"is a one-pattern\n  histogram, whose entropy is the constant "
          f"{entropy_of_counts([1], 1)!r}, and a two-triple\n  window takes "
          f"{sorted({round(entropy_of_counts(c, 2), 12) for c in ((2,), (1, 1))})}")
    two = ts_perment_20(close, length=4).dropna()
    print(f"  measured at length=4 on a 400-bar walk: distinct values "
          f"{sorted(two.round(12).unique())}")

    print("\n  a close that is not finite")
    for bad in (np.nan, np.inf, -np.inf):
        c = close.to_numpy().copy()
        c[200] = bad
        v = ts_perment_20(Series(c, index=close.index))
        base = ts_perment_20(close)
        emptied = [int(i) for i in np.flatnonzero(v.isna() & base.notna())]
        print(f"    close[200]={bad}: bars emptied {len(emptied)} "
              f"{emptied[:3]}..{emptied[-3:] if emptied else []}")
    print("  a non-positive or subnormal close is NOT rejected -- the column "
          "takes no\n  ratio, so it still has a place in the ordering:")
    for bad in (0.0, -5.0, 1e-310):
        c = close.to_numpy().copy()
        c[200] = bad
        v = ts_perment_20(Series(c, index=close.index))
        print(f"    close[200]={bad!r}: fires {int(v.notna().sum())} of "
              f"{len(close)}, bar 200 = {float(v.iloc[200])!r}")

    print("\n  fillna, and distinct names")
    print(f"    fillna=0 leaves "
          f"{int(ts_perment_20(close, fillna=0).isna().sum())} NaNs")
    for length in (20, 40):
        print(f"    length={length}: {ts_perment_20(close, length=length).name}")

    print("\n  the accessor and the registration")
    import pandas as pd
    import pandas_ta as ta
    df = pd.DataFrame({"close": close.to_numpy()})
    acc = df.ta.ts_perment_20()
    print(f"    df.ta.ts_perment_20() -> {acc.name}, "
          f"equals the function: "
          f"{bool(acc.equals(ts_perment_20(df['close'])))}")
    print(f"    df.ta.ts_perment_20(length=40) -> "
          f"{df.ta.ts_perment_20(length=40).name}")
    print(f"    in Category['statistics']: "
          f"{'ts_perment_20' in ta.Category['statistics']}")


# ---------------------------------------------------------------- the cost


def cost():
    head("Cost")
    for n in (10000, 100000, 400000):
        close = walk(n, seed=12)
        best = min(_timed(close) for _ in range(3))
        tracemalloc.start()
        ts_perment_20(close)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(f"  n={n}: best of three {best * 1000:.0f} ms, traced peak "
              f"{peak / 1e6:.1f} MB; one bool window array is "
              f"{(n - LENGTH + 1) * TRIPLES / 1e6:.1f} MB and the int8 code "
              f"array {(n - 2) / 1e6:.1f} MB")


def _timed(close):
    t0 = time.perf_counter()
    ts_perment_20(close)
    return time.perf_counter() - t0


SECTIONS = {
    "source": source,
    "gate_a": gate_a,
    "gate_b": gate_b,
    "gate_c_d": gate_c_d,
    "attainable": attainable,
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
