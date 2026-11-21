"""Investigation harness for PandasTa issue #129 (C22-RS-RANGE), catch22's
`SC_FluctAnal_2_rsrangefit_50_1_logi_prop_r1`.

This is the receipt for a MEASURED REVERT, not a shipped port: see
`docs/C22RsRangeMeasured.md`. No `pandas_ta/statistics/c22_rs_range.py` was
written, because every candidate algorithm built here from the public,
non-GPL literature on rescaled-range / fluctuation analysis (Hurst 1951;
Mandelbrot & Wallis 1969; Peng et al. 1994's generalisation to a q-order
fluctuation function, which this repo's own `g191_165` already implements
for the plain single-scale R/S statistic) failed to reproduce the reference
`pycatch22` 1.0.2 (GPL-3.0) output closely enough to support a correctness
claim. `pycatch22` is installed in this worktree and is used BELOW ONLY AS A
BLACK-BOX NUMERIC ORACLE -- called, never read -- exactly the use the issue's
own screen prototype makes of it ("it is used here only to MEASURE, on the
owner's machine").

A bare `python docs/measure_c22_rs_range.py` runs only FSANITY (~1s): the
section that builds and sanity-checks the candidate fluctuation functions on
SYNTHETIC series and never imports the reference. TAU and SEARCH call
`pycatch22` and are OPT-IN, same discipline `docs/C22PeriodicityMeasured.md`
section P uses and `docs/measure_c22_ami2.py` states explicitly: neither runs,
and `pycatch22` is not imported, unless named on the command line --
`python docs/measure_c22_rs_range.py TAU SEARCH` (~60s). Each opens with an
`importlib.util.find_spec("pycatch22")` check and reports ABSENT rather than
raising if the dev-only package is not installed.

    TAU      pins the log-spaced tau (window-size) grid by matching the
             reference's output DENOMINATOR (every observed value is an
             exact multiple of 1/N_tau) across seven series lengths.
    FSANITY  checks the fluctuation function F(tau) this harness builds is a
             sane generalised Hurst/DFA estimator (the right ORDERING for
             persistent vs anti-persistent synthetic series), independent of
             whether it reproduces `prop_r1`.
    SEARCH   the grid search over fluctuation-function variants and
             breakpoint-choice criteria for the output itself, and the
             correlations each achieves against the reference -- the
             evidence that none is close enough to ship.
"""
import importlib.util
import sys

import numpy as np

REF_NAME = "SC_FluctAnal_2_rsrangefit_50_1_logi_prop_r1"
REF_DFA_NAME = "SC_FluctAnal_2_dfa_50_1_2_logi_prop_r1"


# ---------------------------------------------------------------------------
# TAU -- the log-spaced window-size grid
# ---------------------------------------------------------------------------

def taus(n, frac=2, tau_min=5):
    """`unique(round(logspace(tau_min, n // frac, 50)))` -- the grid whose
    SIZE this section pins against the reference's output denominator."""
    tau_max = n // frac
    t = np.unique(np.round(np.logspace(np.log10(tau_min), np.log10(tau_max), 50)).astype(int))
    return t[(t >= tau_min) & (t <= tau_max)]


def _denominator(vals, max_d=200):
    """Smallest D <= max_d with every val * D close to an integer."""
    for d in range(1, max_d + 1):
        if all(abs(v * d - round(v * d)) < 1e-6 for v in vals):
            return d
    return None


def section_tau():
    if importlib.util.find_spec("pycatch22") is None:
        print("pycatch22 ABSENT -- TAU cannot run (dev-only, GPL-3.0 oracle)")
        return
    import pycatch22
    ref_rs = pycatch22.SC_FluctAnal_2_rsrangefit_50_1_logi_prop_r1
    ref_dfa = pycatch22.SC_FluctAnal_2_dfa_50_1_2_logi_prop_r1
    rng = np.random.default_rng(5)
    print("-- TAU: observed output denominator vs this grid's |taus| --")
    print("rs_range: tau_min=5, tau_max=n//2 (12 samples per n)")
    for n in (100, 90, 80, 70, 60, 50, 45, 40):
        vals = [ref_rs(rng.normal(size=n).tolist()) for _ in range(12)]
        d = _denominator(vals)
        grid = len(taus(n, frac=2))
        print(f"  n={n:3d}  observed denom={d!s:>4}  |taus(frac=2)|={grid}  "
              f"{'MATCH' if d == grid else 'no match (degenerate below ~45)'}")
    print("dfa: tau_min=5, tau_max=n//4 (12 samples per n)")
    for n in (100, 90, 80, 70):
        vals = [ref_dfa(rng.normal(size=n).tolist()) for _ in range(12)]
        d = _denominator(vals)
        grid = len(taus(n, frac=4))
        print(f"  n={n:3d}  observed denom={d!s:>4}  |taus(frac=4)|={grid}  "
              f"{'MATCH' if d == grid else 'no match (degenerate below ~90)'}")

    print()
    print("sensitivity: does tau_min=4 or 6 ALSO match at n=100 and n=70?")
    print("(a cardinality match does not by itself prove tau_min=5 is unique --")
    print("this checks whether an off-by-one in tau_min is distinguishable at all)")
    for n in (100, 70):
        vals = [ref_rs(rng.normal(size=n).tolist()) for _ in range(12)]
        d = _denominator(vals)
        for tm in (4, 5, 6):
            grid = len(taus(n, frac=2, tau_min=tm))
            print(f"  n={n:3d} tau_min={tm}: |taus|={grid}  "
                  f"{'matches observed denom ' + str(d) if grid == d else 'does not match ' + str(d)}")


# ---------------------------------------------------------------------------
# FSANITY -- is the fluctuation function a sane generalised Hurst estimator?
# ---------------------------------------------------------------------------

def log_f_dfa(x, tau_values, order=2):
    """Peng et al. 1994 DFA-`order` fluctuation: polynomial-detrend each
    non-overlapping box of the GLOBAL profile, RMS residual."""
    x = np.asarray(x, dtype=float)
    n = x.size
    profile = np.cumsum(x - x.mean())
    logf = np.empty(len(tau_values))
    for j, tau in enumerate(tau_values):
        boxes = n // tau
        seg = profile[:boxes * tau].reshape(boxes, tau)
        t = np.arange(tau, dtype=float)
        A = np.vstack([t ** p for p in range(order + 1)]).T
        coef, *_ = np.linalg.lstsq(A, seg.T, rcond=None)
        resid = seg - (A @ coef).T
        f = np.sqrt(np.mean(resid ** 2))
        logf[j] = np.log(f) if f > 0 else np.nan
    return np.log(tau_values.astype(float)), logf


def log_f_rs_classical(x, tau_values, q=2):
    """Classical per-box R/S (Hurst 1951): box's own mean and std (`ddof=1`,
    matching this repo's `g191_165`, `pandas_ta/statistics/g191_165.py:134`)
    for one fixed window length."""
    x = np.asarray(x, dtype=float)
    n = x.size
    logf = np.empty(len(tau_values))
    for j, tau in enumerate(tau_values):
        boxes = n // tau
        seg = x[:boxes * tau].reshape(boxes, tau)
        d = seg - seg.mean(axis=1, keepdims=True)
        z = np.cumsum(d, axis=1)
        r = z.max(axis=1) - z.min(axis=1)
        s = seg.std(axis=1, ddof=1)
        rs = np.where(s > 0, r / np.where(s > 0, s, 1.0), np.nan)
        valid = rs[np.isfinite(rs)]
        f = np.sqrt(np.mean(valid ** q)) if valid.size else np.nan
        logf[j] = np.log(f) if f > 0 else np.nan
    return np.log(tau_values.astype(float)), logf


def log_f_range_order0(x, tau_values):
    """RMS over boxes of (max - min) of the box after removing the box's OWN
    mean, undivided -- the best-correlating candidate found in SEARCH."""
    x = np.asarray(x, dtype=float)
    n = x.size
    logf = np.empty(len(tau_values))
    for j, tau in enumerate(tau_values):
        boxes = n // tau
        seg = x[:boxes * tau].reshape(boxes, tau)
        resid = seg - seg.mean(axis=1, keepdims=True)
        z = np.cumsum(resid, axis=1)
        r = z.max(axis=1) - z.min(axis=1)
        f = np.sqrt(np.mean(r ** 2))
        logf[j] = np.log(f) if f > 0 else np.nan
    return np.log(tau_values.astype(float)), logf


def log_f_range_global(x, tau_values, order=2):
    """DFA machinery (polynomial-detrend each box of the GLOBAL cumulative
    profile, order 2 -- `log_f_dfa`'s construction) with a RANGE statistic
    per box instead of an RMS residual: the most literal reading of
    "rsrangefit" inside a fluctuation-analysis frame. NOT separately
    FSANITY-checked -- it reuses `log_f_dfa`'s validated global profile and
    swaps only the per-box summary."""
    x = np.asarray(x, dtype=float)
    n = x.size
    profile = np.cumsum(x - x.mean())
    logf = np.empty(len(tau_values))
    for j, tau in enumerate(tau_values):
        boxes = n // tau
        seg = profile[:boxes * tau].reshape(boxes, tau)
        t = np.arange(tau, dtype=float)
        A = np.vstack([t ** p for p in range(order + 1)]).T
        coef, *_ = np.linalg.lstsq(A, seg.T, rcond=None)
        resid = seg - (A @ coef).T
        r = resid.max(axis=1) - resid.min(axis=1)
        f = np.sqrt(np.mean(r ** 2))
        logf[j] = np.log(f) if f > 0 else np.nan
    return np.log(tau_values.astype(float)), logf


def _ols_slope(logt, logf):
    mask = np.isfinite(logf)
    A = np.vstack([logt[mask], np.ones(mask.sum())]).T
    coef, *_ = np.linalg.lstsq(A, logf[mask], rcond=None)
    return coef[0]


def section_fsanity():
    rng = np.random.default_rng(8)
    print("-- FSANITY: single-fit log-log slope, by AR(1) persistence --")
    print(f"{'series':<10} {'dfa order2':>12} {'rs classical':>14} {'range order0':>14}")
    for label, phi in (("white", 0.0), ("AR+0.9", 0.9), ("AR-0.9", -0.9)):
        slopes = {"dfa": [], "rs": [], "range0": []}
        for _ in range(20):
            ar = np.zeros(100)
            for i in range(1, 100):
                ar[i] = phi * ar[i - 1] + rng.normal()
            slopes["dfa"].append(_ols_slope(*log_f_dfa(ar, taus(100, frac=4))))
            slopes["rs"].append(_ols_slope(*log_f_rs_classical(ar, taus(100, frac=2))))
            slopes["range0"].append(_ols_slope(*log_f_range_order0(ar, taus(100, frac=2))))
        print(f"{label:<10} {np.mean(slopes['dfa']):>12.4f} {np.mean(slopes['rs']):>14.4f} "
              f"{np.mean(slopes['range0']):>14.4f}")
    print("Expected ordering AR+0.9 > white > AR-0.9 holds for every column above:")
    print("this harness's fluctuation functions ARE generalised Hurst/DFA estimators.")


# ---------------------------------------------------------------------------
# SEARCH -- the breakpoint-choice grid search for `prop_r1` itself
# ---------------------------------------------------------------------------

def _best_break(logt, logf, min_side):
    """argmin over k of the two-piece (disconnected) OLS SSE; returns the
    1-indexed size of the LEFT segment and the total point count."""
    n = len(logt)
    best_sse, best_k = np.inf, None
    for k in range(min_side, n - min_side + 1):
        sse = 0.0
        for a, b in ((0, k), (k, n)):
            xs, ys = logt[a:b], logf[a:b]
            A = np.vstack([xs, np.ones_like(xs)]).T
            coef, *_ = np.linalg.lstsq(A, ys, rcond=None)
            sse += np.sum((ys - A @ coef) ** 2)
        if sse < best_sse:
            best_sse, best_k = sse, k
    return best_k, n


def _midrank(a):
    """Average rank within each group of equal values (ties share the mean
    of the ranks they'd occupy), not position-broken -- both the reference
    and every candidate here live on a coarse `1/35`-style lattice, so ties
    are frequent by construction and a position-broken rank would overstate
    agreement."""
    order = np.argsort(a, kind="stable")
    sorted_a = a[order]
    ranks = np.empty(len(a))
    i = 0
    while i < len(a):
        j = i
        while j + 1 < len(a) and sorted_a[j + 1] == sorted_a[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1
        i = j + 1
    return ranks


def _spearman(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    ra, rb = _midrank(a), _midrank(b)
    return np.corrcoef(ra, rb)[0, 1]


def _best_break_connected(logt, logf, min_side):
    """Continuous (connected-at-the-knot) two-piece fit: one line with a
    kink at `logt[k-1]`, fit in a single lstsq rather than two independent
    ones. Returns the 1-indexed knot position and the point count."""
    n = len(logt)
    best_sse, best_k = np.inf, None
    for k in range(min_side, n - min_side + 1):
        knot = logt[k - 1]
        b2 = np.minimum(logt - knot, 0.0)
        b3 = np.maximum(logt - knot, 0.0)
        A = np.column_stack([np.ones_like(logt), b2, b3])
        coef, *_ = np.linalg.lstsq(A, logf, rcond=None)
        sse = np.sum((logf - A @ coef) ** 2)
        if sse < best_sse:
            best_sse, best_k = sse, k
    return best_k, n


def _cusum_break(logt, logf):
    """Single-line OLS fit; changepoint = argmax |cumsum(residuals)|."""
    n = len(logt)
    A = np.vstack([logt, np.ones_like(logt)]).T
    coef, *_ = np.linalg.lstsq(A, logf, rcond=None)
    resid = logf - A @ coef
    k = int(np.argmax(np.abs(np.cumsum(resid)))) + 1
    return k, n


def _posresid_count(logt, logf):
    """No search: count of points above a single overall OLS fit."""
    n = len(logt)
    A = np.vstack([logt, np.ones_like(logt)]).T
    coef, *_ = np.linalg.lstsq(A, logf, rcond=None)
    resid = logf - A @ coef
    return int(np.sum(resid > 0)), n


CRITERIA = {
    "disconnected two-piece (left)": lambda lt, lf, ms: (lambda k, n: (k, n))(*_best_break(lt, lf, ms)),
    "disconnected two-piece (right)": lambda lt, lf, ms: (lambda k, n: (n - k, n))(*_best_break(lt, lf, ms)),
    "connected two-piece (left)": lambda lt, lf, ms: _best_break_connected(lt, lf, ms),
    "CUSUM of single-fit residual": lambda lt, lf, ms: _cusum_break(lt, lf),
    "positive-residual count (no search)": lambda lt, lf, ms: _posresid_count(lt, lf),
}


def candidate(x, f_fn, frac, min_side, criterion_fn):
    t = taus(len(x), frac=frac)
    logt, logf = f_fn(x, t)
    mask = np.isfinite(logf)
    if mask.sum() < 2 * min_side:
        return 1.0
    k, n = criterion_fn(logt[mask], logf[mask], min_side)
    return k / n


def section_search():
    if importlib.util.find_spec("pycatch22") is None:
        print("pycatch22 ABSENT -- SEARCH cannot run (dev-only, GPL-3.0 oracle)")
        return
    import pycatch22
    ref_rs = pycatch22.SC_FluctAnal_2_rsrangefit_50_1_logi_prop_r1
    ref_dfa = pycatch22.SC_FluctAnal_2_dfa_50_1_2_logi_prop_r1
    rng = np.random.default_rng(11)
    xs = [rng.normal(size=100) for _ in range(100)]
    refs_rs = [ref_rs(x.tolist()) for x in xs]
    refs_dfa = [ref_dfa(x.tolist()) for x in xs]

    f_variants = {
        "range_order0": (log_f_range_order0, 2),
        "classical R/S (local mean+std)": (log_f_rs_classical, 2),
        "DFA order2 (global profile, RMS)": (log_f_dfa, 4),
        "DFA order2 (global profile, range)": (log_f_range_global, 4),
    }

    print("-- SEARCH: every (F(tau), breakpoint criterion, min_side) combination this")
    print("   harness implements, against the rs_range reference --")
    print(f"{'F(tau)':<32} {'criterion':<34} {'min_side':>9} {'exact':>7} {'pearson':>9} {'spearman':>10}")
    best = (-2.0, None)
    for fname, (f_fn, frac) in f_variants.items():
        for crit_name, crit_fn in CRITERIA.items():
            for min_side in (2, 5, 9, 12):
                cands = [candidate(x, f_fn, frac, min_side, crit_fn) for x in xs]
                exact = sum(1 for r, c in zip(refs_rs, cands) if abs(r - c) < 1e-9)
                pear = np.corrcoef(refs_rs, cands)[0, 1] if np.std(cands) > 0 else float("nan")
                sp = _spearman(refs_rs, cands) if np.std(cands) > 0 else float("nan")
                print(f"{fname:<32} {crit_name:<34} {min_side:>9} {exact:>4}/{len(xs):<3} "
                      f"{pear:>9.3f} {sp:>10.3f}")
                if pear == pear and pear > best[0]:
                    best = (pear, (fname, crit_name, min_side, exact))
    print()
    print(f"BEST against rs_range over {len(f_variants) * len(CRITERIA) * 4} combinations: "
          f"pearson={best[0]:.3f}, {best[1]}")

    # Same criteria against the DFA sibling, using log_f_dfa -- NOT an
    # isolation of the breakpoint step from the fluctuation function: §A2
    # only sanity-checked log_f_dfa's ORDERING on synthetic AR(1) series, it
    # was never shown to be the reference's own F(tau), so a low rho here is
    # consistent with either hypothesis and proves neither.
    print()
    print("-- same criteria against the DFA sibling, F(tau) = log_f_dfa --")
    best_dfa = (-2.0, None)
    for crit_name, crit_fn in CRITERIA.items():
        for min_side in (2, 5, 9, 12):
            cands = [candidate(x, log_f_dfa, 4, min_side, crit_fn) for x in xs]
            pear = np.corrcoef(refs_dfa, cands)[0, 1] if np.std(cands) > 0 else float("nan")
            if pear == pear and pear > best_dfa[0]:
                best_dfa = (pear, (crit_name, min_side))
    print(f"BEST against the dfa reference: pearson={best_dfa[0]:.3f}, {best_dfa[1]}")
    print(f"Neither sibling clears pearson 0.4 ({best[0]:.3f} for rs_range, "
          f"{best_dfa[0]:.3f} for dfa). Compare c22_periodicity's disambiguation")
    print("table, which matched its reference on 2,798 / 2,802 windows once the right")
    print("reading was found -- the gap here is qualitative, not a rounding margin,")
    print("across all hypotheses in this harness's family, and is why this issue is")
    print("closed as a measured revert rather than a further search.")


SECTIONS = {"TAU": section_tau, "FSANITY": section_fsanity, "SEARCH": section_search}
DEFAULT = ["FSANITY"]

if __name__ == "__main__":
    requested = sys.argv[1:] or DEFAULT
    for name in requested:
        SECTIONS[name]()
        print()
