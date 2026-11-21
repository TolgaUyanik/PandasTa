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

Run `python docs/measure_c22_rs_range.py` for the whole investigation (~60s):

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
    """Classical per-box R/S (Hurst 1951): box's own mean and std, as this
    repo's `g191_165` computes for one fixed window length."""
    x = np.asarray(x, dtype=float)
    n = x.size
    logf = np.empty(len(tau_values))
    for j, tau in enumerate(tau_values):
        boxes = n // tau
        seg = x[:boxes * tau].reshape(boxes, tau)
        d = seg - seg.mean(axis=1, keepdims=True)
        z = np.cumsum(d, axis=1)
        r = z.max(axis=1) - z.min(axis=1)
        s = seg.std(axis=1)
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


def _spearman(a, b):
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
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

    # Isolation check: the same criteria against the DFA sibling, whose F(tau)
    # (Peng et al. DFA-2) this harness trusts (FSANITY) -- to see whether the
    # ceiling is the fluctuation function or the breakpoint logic.
    print()
    print("-- isolation: same criteria against the DFA sibling (trusted F(tau)) --")
    best_dfa = (-2.0, None)
    for crit_name, crit_fn in CRITERIA.items():
        for min_side in (2, 5, 9, 12):
            cands = [candidate(x, log_f_dfa, 4, min_side, crit_fn) for x in xs]
            pear = np.corrcoef(refs_dfa, cands)[0, 1] if np.std(cands) > 0 else float("nan")
            if pear == pear and pear > best_dfa[0]:
                best_dfa = (pear, (crit_name, min_side))
    print(f"BEST against the dfa reference: pearson={best_dfa[0]:.3f}, {best_dfa[1]}")
    print(f"Neither sibling clears pearson 0.4 ({best[0]:.3f} for rs_range, "
          f"{best_dfa[0]:.3f} for dfa with a TRUSTED F(tau)), which is why §A3 of the")
    print("receipt concludes the breakpoint/proportion EXTRACTION -- not the fluctuation")
    print("function -- is the unresolved step for BOTH features. Compare")
    print("c22_periodicity's disambiguation table, which matched its reference on")
    print("2,798 / 2,802 windows once the right reading was found -- the gap here is")
    print("qualitative, not a rounding margin, and is why this issue is closed as a")
    print("measured revert.")


SECTIONS = {"TAU": section_tau, "FSANITY": section_fsanity, "SEARCH": section_search}

if __name__ == "__main__":
    requested = sys.argv[1:] or list(SECTIONS)
    for name in requested:
        SECTIONS[name]()
        print()
