# -*- coding: utf-8 -*-
"""C22-TRANSITION-VARIANCE (PandasTa issue #130): grid-search probe for
`SB_TransitionMatrix_quantile_3_ac_sumdiagcov` -- catch22's trace of the
covariance of a 3-state return transition matrix.

    python docs/measure_c22_transition_variance.py        # FSANITY (no oracle)
    python docs/measure_c22_transition_variance.py SEARCH  # the GPL-3.0 black box

This is the harness behind a MEASURED REVERT
(`docs/C22TransitionVarianceMeasured.md`): **no `pandas_ta` module was
shipped**, so unlike this fork's other `measure_c22_*.py` scripts this one is
fully self-contained -- it defines its own candidate symbolisation,
transition-matrix and covariance pipelines rather than importing a shipped
one, the same shape `docs/measure_c22_rs_range.py` uses for the same reason.

Section **SEARCH** is OPT-IN and is the only part of this repository that
runs the reference implementation (pycatch22, **GPL-3.0**). It is
MEASUREMENT only -- the same use the owner's own screen prototype makes of it
(`docs/issues/screen/ind_screen_r3.py`) -- and no shipped module imports it,
because none was shipped. hctsa's own MATLAB source is not in this tree and
was not read: the candidate pipelines below are built from the catch22
paper's own one-line description of the feature ("trace of covariance of
transition matrix between symbols in equiprobable 3-letter alphabet") and
are picked by fitting their OUTPUT to the reference's OUTPUT as a black box,
the same discipline `docs/measure_c22_rs_range.py` and
`docs/measure_c22_dfa.py` section Q use.

Gate E does not apply: there is no shipped `Category` column to run it
against.
"""
from __future__ import annotations

import importlib.util
import math
import sys

import numpy as np
import pandas as pd

LENGTH = 100
N = 1500
NUM_STATES = 3


# --------------------------------------------------------------- frames
def walk(n=N, seed=11, sigma=0.015, level=100.0):
    rng = np.random.default_rng(seed)
    return pd.Series(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def tick_rounded(n=N, seed=55):
    return pd.Series(np.round(walk(n, seed).to_numpy(), 2))


def penny(n=N, seed=23, level=2.0, sigma=0.012):
    """A 2-lira stock on a 1-kurus tick: many returns are exactly 0."""
    return pd.Series(np.round(walk(n, seed, sigma, level).to_numpy(), 2))


def ar1(n=N, seed=7, sigma=0.01, phi=0.6):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = e[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + e[t]
    return pd.Series(100.0 * np.cumprod(1.0 + r))


def cosine_returns(n=N, period=20.0, amp=0.01):
    t = np.arange(n, dtype=float)
    return pd.Series(100.0 * np.cumprod(1.0 + amp * np.cos(2 * np.pi * t / period)))


def student_t(n=N, seed=19, df=3, sigma=0.01):
    rng = np.random.default_rng(seed)
    r = sigma * rng.standard_t(df, n)
    return pd.Series(100.0 * np.cumprod(1.0 + np.clip(r, -0.5, 0.5)))


FRAMES = {
    "walk": walk(),
    "tick-rounded": tick_rounded(),
    "penny": penny(),
    "ar1": ar1(),
    "cosine": cosine_returns(),
    "student-t": student_t(),
}


def returns(close):
    c = np.asarray(close, float)
    return c[1:] / c[:-1] - 1.0


def windows(close, length=LENGTH):
    r = returns(close)
    win = np.lib.stride_tricks.sliding_window_view(r, length)
    return win, np.arange(length, length + win.shape[0])


def head(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def row(*cells):
    print(" | ".join(str(c) for c in cells))


def spearman(a, b):
    x, y = pd.Series(np.asarray(a, float)), pd.Series(np.asarray(b, float))
    m = x.notna() & y.notna()
    if int(m.sum()) < 3:
        return float("nan")
    rx, ry = x[m].rank(), y[m].rank()
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


# ------------------------------------------------- candidate pipelines
def symbolize(window, method, k=NUM_STATES):
    """Assign every point of `window` (1-D) to one of `k` symbols by its
    EQUIPROBABLE quantile bin, or `None` for a window with no variation.

    Each `method` is a defensible reading of "equiprobable quantile bins":

    * `quantile-hctsa`: quantile VALUE thresholds, half-open `(lo, hi]`
      intervals, the lowest threshold pushed down by 1 so the minimum point
      is included in the first bin.
    * `quantile-ge-lt`: the same thresholds, half-open `[lo, hi)` intervals
      (the last bin closed on both ends).
    * `quantile-rank-first`: EQUAL-COUNT bins by sort rank, ties broken by
      original position (a stable sort).
    * `quantile-rank-average`: equal-count bins by AVERAGE rank over tied
      values.
    """
    w = np.asarray(window, dtype=float)
    n = w.size
    if not np.all(np.isfinite(w)):
        return None
    sd = float(w.std(ddof=1))
    if not (np.isfinite(sd) and sd > 0.0):
        return None

    if method in ("quantile-rank-first", "quantile-rank-average"):
        order = np.argsort(w, kind="stable")
        if method == "quantile-rank-first":
            ranks = np.empty(n, dtype=np.int64)
            ranks[order] = np.arange(n)
            return np.minimum((ranks * k) // n, k - 1)
        sorted_w = w[order]
        avg_ranks = np.empty(n, dtype=float)
        i = 0
        while i < n:
            j = i
            while j + 1 < n and sorted_w[j + 1] == sorted_w[i]:
                j += 1
            avg_ranks[order[i:j + 1]] = (i + j) / 2.0
            i = j + 1
        return np.minimum((avg_ranks * k / n).astype(np.int64), k - 1)

    qs = np.quantile(w, np.linspace(0.0, 1.0, k + 1))
    labels = np.zeros(n, dtype=np.int64)
    if method == "quantile-hctsa":
        th = qs.copy()
        th[0] -= 1.0
        for i in range(k):
            labels[(w > th[i]) & (w <= th[i + 1])] = i
        return labels
    if method == "quantile-ge-lt":
        for i in range(k):
            if i == k - 1:
                labels[(w >= qs[i]) & (w <= qs[i + 1])] = i
            else:
                labels[(w >= qs[i]) & (w < qs[i + 1])] = i
        return labels
    raise ValueError(method)


def firstzero_simple(w):
    """The classic CO_FirstZero reading: smallest tau >= 1 with sample
    autocorrelation(tau) <= 0, else `n // 2`. NOT this fork's `firstzero_ac`
    module, which is Kats' different "first negative right after a
    positive" rule -- this is the other, simpler convention, tried here as
    its own candidate rather than imported, so the two cannot be confused."""
    n = w.size
    x = w - w.mean()
    var0 = float(np.dot(x, x))
    if not (var0 > 0):
        return 1
    for tau in range(1, n // 2 + 1):
        ac = float(np.dot(x[:-tau], x[tau:])) / var0
        if ac <= 0.0:
            return tau
    return n // 2


def transitions_at_lag(labels, tau, k=NUM_STATES, normalize="row"):
    """The `k x k` transition matrix of `labels` at lag `tau`, under one of
    three normalisations: `row` (row-stochastic: P(next = j | current = i)),
    `total` (joint: count / pair count), `none` (raw counts). `None` if it
    cannot be formed, or (for `row`) if an origin symbol never occurs."""
    if labels is None or tau < 1 or tau >= labels.size:
        return None
    a, b = labels[:-tau], labels[tau:]
    counts = np.zeros((k, k), dtype=float)
    for i in range(k):
        ai = a == i
        if not ai.any():
            if normalize == "row":
                return None
            continue
        bi = b[ai]
        for j in range(k):
            counts[i, j] = float(np.sum(bi == j))
    if normalize == "row":
        rowsum = counts.sum(axis=1, keepdims=True)
        if np.any(rowsum[:, 0] <= 0):
            return None
        return counts / rowsum
    if normalize == "total":
        total = counts.sum()
        return None if total <= 0 else counts / total
    return counts


def candidate(window, symb="quantile-hctsa", normalize="row", ddof=1,
             axis="rows", tau=1):
    """One candidate pipeline's value on one window: symbolise, form the
    transition matrix at lag `tau`, take the covariance over its rows (or
    columns, or the whole matrix flattened) and trace it (or, for
    `axis="flatten"`, just the flat variance)."""
    w = np.asarray(window, float)
    labels = symbolize(w, method=symb, k=NUM_STATES)
    if labels is None:
        return float("nan")
    t = firstzero_simple(w) if tau == "ac0" else tau
    T = transitions_at_lag(labels, t, k=NUM_STATES, normalize=normalize)
    if T is None:
        return float("nan")
    if axis == "flatten":
        return float(np.var(T.ravel(), ddof=ddof))
    M = T if axis == "rows" else T.T
    C = np.cov(M, rowvar=False, ddof=ddof)
    return float(np.trace(np.atleast_2d(C)))


SYMB_METHODS = ["quantile-hctsa", "quantile-ge-lt", "quantile-rank-first",
               "quantile-rank-average"]
NORMALIZE = ["row", "total", "none"]
AXES = ["rows", "cols", "flatten"]
DDOFS = [0, 1]
TAUS = [1, 2, 3, 4, 5, "ac0"]


def section_fsanity():
    head("FSANITY. Structural sanity of the candidate pipelines (no oracle)")
    print("Every symbolisation gives each of the 3 symbols roughly n/3")
    print("occurrences on a window with no ties, and a row-normalised")
    print("transition matrix's rows sum to 1 -- checked here, before the")
    print("GPL-3.0 oracle is in the loop at all.")
    win, _ = windows(FRAMES["walk"])
    row("symb", "windows checked", "min/max symbol share", "row-stochastic?")
    for symb in SYMB_METHODS:
        shares, stoch = [], True
        for i in range(0, win.shape[0], 97):
            labels = symbolize(win[i], method=symb, k=NUM_STATES)
            if labels is None:
                continue
            _, counts = np.unique(labels, return_counts=True)
            shares.append(counts.min() / counts.sum())
            shares.append(counts.max() / counts.sum())
            T = transitions_at_lag(labels, 1, k=NUM_STATES, normalize="row")
            if T is not None:
                stoch &= bool(np.allclose(T.sum(axis=1), 1.0))
        row(symb, win.shape[0] // 97, f"[{min(shares):.3f}, {max(shares):.3f}]",
            stoch)

    head("FSANITY2. Monotone invariance of the symbolisation")
    print("A quantile-based symbol assignment depends only on RANK, so it")
    print("should be unchanged under any strictly increasing map of the")
    print("window -- checked against an affine rescale and a nonlinear one")
    print("(cube), on windows with no exact ties.")
    for symb in SYMB_METHODS:
        moved_affine = moved_cube = seen = 0
        for i in range(0, win.shape[0], 23):
            w = win[i]
            base = symbolize(w, method=symb, k=NUM_STATES)
            if base is None:
                continue
            seen += 1
            affine = symbolize(w * 3.0 + 1.0, method=symb, k=NUM_STATES)
            cube = symbolize(np.sign(w) * np.abs(w) ** 3, method=symb,
                             k=NUM_STATES)
            moved_affine += int(not np.array_equal(base, affine))
            moved_cube += int(not np.array_equal(base, cube))
        row(symb, f"seen {seen}", f"moved under affine {moved_affine}",
            f"moved under cube {moved_cube}")


def section_search():
    head("SEARCH. The reference implementation as a BLACK BOX (GPL-3.0, opt-in)")
    print("pycatch22 is GPL-3.0 and this fork is MIT. Run here to MEASURE")
    print("only, to see whether any candidate pipeline above reproduces the")
    print("named feature -- never read as source.")
    if importlib.util.find_spec("pycatch22") is None:
        row("pycatch22", "ABSENT -- section SEARCH cannot run")
        return
    import pycatch22

    probe = pycatch22.catch22_all(
        [float(v) for v in returns(FRAMES["walk"])[:LENGTH]],
        short_names=True)
    names = [n for n in probe["short_names"] if "ransition" in n]
    row("catch22_all names matching 'ransition'", names)
    if not names:
        row("no matching feature name -- cannot proceed")
        return
    which = probe["short_names"].index(names[0])

    def ref(window):
        out = pycatch22.catch22_all([float(v) for v in window],
                                    short_names=True)
        return float(out["values"][which])

    head("SEARCH1. The reference's own value, cached once per window")
    win_sets = {name: windows(FRAMES[name])[0] for name in FRAMES}
    idx_by_frame = {name: list(range(0, w.shape[0], 23))
                    for name, w in win_sets.items()}
    ref_cache = {(name, i): ref(win_sets[name][i])
                for name in FRAMES for i in idx_by_frame[name]}
    row("frame x stride-23 windows", sum(len(v) for v in idx_by_frame.values()))
    finite_ref = [v for v in ref_cache.values() if math.isfinite(v)]
    row("reference value range", f"[{min(finite_ref):.6f}, {max(finite_ref):.6f}]",
        f"median {np.median(finite_ref):.6f}")

    head("SEARCH2. Every candidate pipeline against the reference (best-first)")
    print(f"{len(SYMB_METHODS)} symbolisations x {len(NORMALIZE)} "
          f"normalisations x {len(AXES)} axes x {len(DDOFS)} ddofs x "
          f"{len(TAUS)} lags = "
          f"{len(SYMB_METHODS) * len(NORMALIZE) * len(AXES) * len(DDOFS) * len(TAUS)} "
          "combinations, all implemented and run, not asserted.")
    results = []
    for symb in SYMB_METHODS:
        for norm in NORMALIZE:
            for axis in AXES:
                for ddof in DDOFS:
                    for tau in TAUS:
                        exact = total = 0
                        gap = 0.0
                        pooled_mine, pooled_ref = [], []
                        for name in FRAMES:
                            for i in idx_by_frame[name]:
                                r = ref_cache[(name, i)]
                                m = candidate(win_sets[name][i], symb, norm,
                                             ddof, axis, tau)
                                pooled_ref.append(r)
                                pooled_mine.append(m)
                                if math.isfinite(r) and math.isfinite(m):
                                    total += 1
                                    if abs(r - m) <= 1e-9:
                                        exact += 1
                                    gap = max(gap, abs(r - m))
                        sp = spearman(pooled_mine, pooled_ref)
                        results.append(((symb, norm, axis, ddof, tau), total,
                                       exact, gap, sp))
    by_exact = sorted(results,
                      key=lambda t: (-t[2], t[3] if math.isfinite(t[3]) else 1e18))
    row("symb", "normalize", "axis", "ddof", "tau", "windows",
        "exact (tol 1e-9)", "max |gap|", "Spearman (pooled)")
    for combo, total, exact, gap, sp in by_exact[:15]:
        symb, norm, axis, ddof, tau = combo
        row(symb, norm, axis, ddof, tau, total, f"{exact} of {total}",
            f"{gap:.3e}", f"{sp:+.4f}")
    head("SEARCH3. Best overall, by exact-match count")
    row("best combo (symb, normalize, axis, ddof, tau)", by_exact[0][0])
    row("exact / windows", f"{by_exact[0][2]} / {by_exact[0][1]}",
        "max |gap|", f"{by_exact[0][3]:.3e}", "Spearman", f"{by_exact[0][4]:+.4f}")

    head("SEARCH4. Best overall, by Spearman rho (a DIFFERENT ranking)")
    print("The exact-match ranking above and this one do not agree on a")
    print("winner -- printed separately rather than quoting one as if it")
    print("were the other.")
    finite_sp = [r for r in results if math.isfinite(r[4])]
    by_sp = sorted(finite_sp, key=lambda t: -t[4])
    row("symb", "normalize", "axis", "ddof", "tau", "windows",
        "exact (tol 1e-9)", "max |gap|", "Spearman (pooled)")
    for combo, total, exact, gap, sp in by_sp[:5]:
        symb, norm, axis, ddof, tau = combo
        row(symb, norm, axis, ddof, tau, total, f"{exact} of {total}",
            f"{gap:.3e}", f"{sp:+.4f}")
    row("best combo (symb, normalize, axis, ddof, tau)", by_sp[0][0])
    row("exact / windows", f"{by_sp[0][2]} / {by_sp[0][1]}",
        "max |gap|", f"{by_sp[0][3]:.3e}", "Spearman", f"{by_sp[0][4]:+.4f}")

    head("SEARCH5. Best row PER NORMALISATION (so the §A2 scale claim is visible)")
    row("normalize", "best combo (symb, axis, ddof, tau)", "exact", "max |gap|",
        "Spearman")
    for norm in NORMALIZE:
        sub = [r for r in results if r[0][1] == norm]
        worst_gap = min((r[3] for r in sub if math.isfinite(r[3])),
                        default=float("nan"))
        best = min(sub, key=lambda t: t[3] if math.isfinite(t[3]) else 1e18)
        gaps = [r[3] for r in sub if math.isfinite(r[3])]
        row(norm, best[0], f"{best[2]} of {best[1]}",
            f"min {min(gaps):.3e} .. max {max(gaps):.3e}", f"{best[4]:+.4f}")


DEFAULT = ["FSANITY"]
SECTIONS = {"FSANITY": section_fsanity, "SEARCH": section_search}

if __name__ == "__main__":
    want = [a.upper() for a in sys.argv[1:]] or DEFAULT
    for key in want:
        SECTIONS[key]()
