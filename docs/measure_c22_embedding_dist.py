# -*- coding: utf-8 -*-
"""Gate A calibration for PandasTa issue #132 (C22-EMBEDDING-DIST).

catch22's `CO_Embed2_Dist_tau_d_expfit_meandiff` is: z-score the series,
pick a delay `tau` (hctsa's `CO_FirstZero(y,'ac')`, the first lag whose
autocorrelation is non-positive, capped near N/10 when none is found),
build the 2-D delay embedding `(y[i], y[i+tau])`, take the Euclidean
distance between EVERY CONSECUTIVE pair of embedded points, fit an
exponential distribution to those distances by maximum likelihood
(`lambda = 1 / mean(d)`), and report the mean absolute difference
between the empirical and fitted distributions of `d`.

That paragraph is everything the paper (Lubba et al. 2019) and hctsa's
published operation description settle; the exact histogram convention
(bin count, bin edges, proportion vs density vs count, or a CDF-based
read instead of a histogram) and the exact delay rule are NOT published
anywhere non-GPL. This script's job is ONLY to check whether the
candidate below, built from that paragraph, reproduces `pycatch22`
1.0.2's OWN output -- used strictly as a BLACK-BOX ORACLE, the same use
this fork's `c22_ami2` and `c22_acf_first_min` make of it (never read
as source, never imported by shipped code -- nothing under
`pandas_ta/` imports it, and this module is not shipped either).

Result, stated in the companion receipt
(`docs/C22EmbeddingDistMeasured.md`): it does not reproduce the oracle
under any of the 35 structural variants tried here (1 broad-sweep
reading + 30 histogram variants + 4 alternative distance/comparison
readings), nor under a further 21-point fine bin sweep of the closest
of those 30 (min-to-max edges, density comparison), which plateaus at a
max error of 0.02-0.05 rather than converging toward zero -- including
ones where `tau` is pinned to 1 by construction (so the delay rule
cannot be the discrepancy). Gate A is UNRESOLVED and PandasTa issue
#132 is
closed as a measured revert: no `pandas_ta` module, test or wiring
entry was added for this feature in this port, because shipping a
column whose correctness could not be checked would be exactly the
"claim written before it was measured" this repository's CLAUDE.md
calls its dominant defect.
"""
import importlib.util

import numpy as np

HAVE_PYCATCH22 = importlib.util.find_spec("pycatch22") is not None


def acf_first_zero(y, cap_n10=True):
    """hctsa's `CO_FirstZero(y, 'ac')`: first lag k >= 1 with acf(k) <= 0."""
    y = np.asarray(y, dtype=float)
    n = y.size
    yo = y - y.mean()
    nfft = 1
    while nfft < 2 * n:
        nfft *= 2
    f = np.fft.fft(yo, n=nfft)
    acov = np.fft.ifft(f * np.conjugate(f))[:n].real / n
    with np.errstate(invalid="ignore", divide="ignore"):
        ac = acov / acov[0]
    tau = n
    for k in range(1, n):
        if ac[k] <= 0:
            tau = k
            break
    if cap_n10:
        cap = max(1, n // 10)
        if tau > cap:
            tau = cap
    return max(1, tau)


def embed2_dist(y, tau):
    y = np.asarray(y, dtype=float)
    n = y.size
    p1 = y[: n - tau]
    p2 = y[tau:]
    dx = np.diff(p1)
    dy = np.diff(p2)
    return np.sqrt(dx * dx + dy * dy)


def expfit_meandiff(d, bins=5, edges="zero_to_max", metric="abs_prop"):
    """The candidate statistic: moment-matched exponential vs a histogram
    of `d`, compared by mean absolute difference of bin PROPORTIONS
    (the only metric consistent with this port's own measured affine
    invariance of the oracle's output -- section A0 below)."""
    if d.size < 2:
        return np.nan
    lam = 1.0 / d.mean()
    lo, hi = (0.0, d.max()) if edges == "zero_to_max" else (d.min(), d.max())
    if hi <= lo:
        return np.nan
    edge_arr = np.linspace(lo, hi, bins + 1)
    counts, _ = np.histogram(d, bins=edge_arr)
    width = edge_arr[1] - edge_arr[0]
    centers = edge_arr[:-1] + width / 2.0
    pdf = lam * np.exp(-lam * centers)
    expected_prop = pdf * width
    actual_prop = counts / d.size
    if metric == "abs_prop":
        return float(np.mean(np.abs(actual_prop - expected_prop)))
    if metric == "abs_count":
        return float(np.mean(np.abs(counts - expected_prop * d.size)))
    if metric == "abs_density":
        actual_density = counts / (d.size * width)
        return float(np.mean(np.abs(actual_density - pdf)))
    raise ValueError(metric)


def candidate(y, bins=5, edges="zero_to_max", metric="abs_prop", cap_n10=True):
    z = (np.asarray(y, dtype=float) - np.mean(y)) / np.std(y, ddof=1)
    tau = acf_first_zero(z, cap_n10=cap_n10)
    d = embed2_dist(z, tau)
    return expfit_meandiff(d, bins=bins, edges=edges, metric=metric), tau


def section_a0_affine_invariance():
    """Is the oracle's output invariant to an affine map of its input?

    It is (checked below), but this does NOT, by itself, rule out a
    raw-density final metric: the candidate z-scores `y` before computing
    `tau`, the embedding or `d` (see `candidate()`), so `d` is already
    invariant to an affine map of the original input before any final
    metric runs on it -- proportion, count and density are then ALL
    invariant downstream of that z-score, and this test cannot distinguish
    between them. (An earlier draft of this script argued density was
    "ruled out analytically" by this invariance; that argument was wrong
    for exactly the reason above, and density is carried into the §A2
    grid instead and tested empirically like everything else.)"""
    import pycatch22

    rng = np.random.default_rng(0)
    y = rng.normal(size=200)
    fn = pycatch22.CO_Embed2_Dist_tau_d_expfit_meandiff
    base = fn(y.tolist())
    cases = {
        "x7.3": fn((y * 7.3).tolist()),
        "+50": fn((y + 50.0).tolist()),
        "x7.3+50": fn((y * 7.3 + 50.0).tolist()),
    }
    print("A0. Affine invariance of the oracle (base=%.12f)" % base)
    for name, val in cases.items():
        print(f"    {name}: {val:.12f}  |diff|={abs(val - base):.2e}")


def section_a1_broad_sweep():
    """25 mixed synthetic frames, the candidate's own tau rule, bins=5,
    zero_to_max, abs_prop -- the single best-effort reading of the public
    definition, checked against the oracle."""
    import pycatch22

    fn = pycatch22.CO_Embed2_Dist_tau_d_expfit_meandiff
    rng = np.random.default_rng(1)
    frames = []
    for i in range(25):
        n = int(rng.integers(60, 300))
        kind = i % 5
        if kind == 0:
            y = rng.normal(size=n)
        elif kind == 1:
            y = np.cumsum(rng.normal(size=n))
        elif kind == 2:
            t = np.arange(n)
            y = np.sin(2 * np.pi * t / 17.0) + 0.1 * rng.normal(size=n)
        elif kind == 3:
            y = np.zeros(n)
            for j in range(1, n):
                y[j] = 0.7 * y[j - 1] + rng.normal()
        else:
            y = rng.standard_t(3, size=n)
        frames.append(y)

    errs = []
    for y in frames:
        ref = fn(y.tolist())
        val, _tau = candidate(y)
        if not (np.isnan(val) or np.isnan(ref)):
            errs.append(abs(val - ref))
    print("A1. Broad sweep, 25 mixed frames, candidate(bins=5, zero_to_max, abs_prop):")
    print(f"    n={len(errs)}  max|err|={max(errs):.6f}  mean|err|={np.mean(errs):.6f}")


def section_a2_tau_pinned():
    """8 strongly anti-persistent frames (acf(1) approx -0.9 by
    construction: alternating sign, so ANY first-zero convention reads
    tau=1 -- this isolates the histogram/fit step from the tau rule."""
    import pycatch22

    fn = pycatch22.CO_Embed2_Dist_tau_d_expfit_meandiff
    rng = np.random.default_rng(7)
    frames = []
    for i in range(8):
        n = int(rng.integers(40, 90))
        y = ((-1.0) ** np.arange(n)) * (1.0 + 0.3 * rng.normal(size=n))
        frames.append(y)
    refs = [fn(y.tolist()) for y in frames]

    acf1 = []
    for y in frames:
        yo = y - y.mean()
        acf1.append(float(np.sum(yo[:-1] * yo[1:]) / np.sum(yo * yo)))
    print("A2. Tau pinned to 1 by construction (acf(1) of the 8 frames):")
    print("    " + ", ".join(f"{v:.3f}" for v in acf1))

    print("    bins  edges        metric       max|err|")
    best = None
    for bins in (3, 5, 10, 20, 40):
        for edges in ("zero_to_max", "min_to_max"):
            for metric in ("abs_prop", "abs_count", "abs_density"):
                errs = []
                for y, ref in zip(frames, refs):
                    d = embed2_dist(np.asarray(y, dtype=float), 1)
                    val = expfit_meandiff(d, bins=bins, edges=edges, metric=metric)
                    errs.append(abs(val - ref))
                m = max(errs)
                print(f"    {bins:4d}  {edges:11s}  {metric:11s}  {m:.6f}")
                if best is None or m < best[0]:
                    best = (m, bins, edges, metric)
    print(f"    best: bins={best[1]} edges={best[2]} metric={best[3]} max|err|={best[0]:.6f}")

    # The winner above (min_to_max / abs_density) is the closest reading
    # found. Sweep its bin count finely to check whether the gap is just
    # "wrong bin count" (would converge to ~0 somewhere in this range) or
    # a genuine residual (stays bounded away from 0 everywhere).
    print("    fine bin sweep of the winner (min_to_max, abs_density), bins 4..24:")
    fine_max, fine_mean = [], []
    for bins in range(4, 25):
        errs = []
        for y, ref in zip(frames, refs):
            d = embed2_dist(np.asarray(y, dtype=float), 1)
            val = expfit_meandiff(d, bins=bins, edges="min_to_max", metric="abs_density")
            errs.append(abs(val - ref))
        fine_max.append(max(errs))
        fine_mean.append(float(np.mean(errs)))
    print(f"    bins 4..24: max|err| ranges {min(fine_max):.6f} .. {max(fine_max):.6f}"
          f" (best at bins={4 + int(np.argmin(fine_max))})")
    print(f"    bins 4..24: mean|err| ranges {min(fine_mean):.6f} .. {max(fine_mean):.6f}")


def section_a3_alt_structures():
    """Structural alternatives to the consecutive-Euclidean-distance,
    histogram-proportion reading: radius-from-origin distance, L1
    distance, all-PAIRS Euclidean distance (not just temporally
    consecutive pairs), and a CDF-based (bin-free) meandiff -- all on the
    same tau-pinned frames as A2."""
    import pycatch22

    fn = pycatch22.CO_Embed2_Dist_tau_d_expfit_meandiff
    rng = np.random.default_rng(7)
    frames = []
    for i in range(8):
        n = int(rng.integers(40, 90))
        y = ((-1.0) ** np.arange(n)) * (1.0 + 0.3 * rng.normal(size=n))
        frames.append(y)
    refs = [fn(y.tolist()) for y in frames]

    def radius_dist(y, tau):
        y = np.asarray(y, dtype=float)
        n = y.size
        p1, p2 = y[: n - tau], y[tau:]
        return np.sqrt(p1 * p1 + p2 * p2)

    def l1_dist(y, tau):
        y = np.asarray(y, dtype=float)
        n = y.size
        p1, p2 = y[: n - tau], y[tau:]
        return np.abs(np.diff(p1)) + np.abs(np.diff(p2))

    def all_pairs_dist(y, tau):
        y = np.asarray(y, dtype=float)
        n = y.size
        p1, p2 = y[: n - tau], y[tau:]
        # Every unordered pair of embedded points, not just consecutive
        # ones -- the upper triangle of the full pairwise distance matrix.
        dx = p1[:, None] - p1[None, :]
        dy = p2[:, None] - p2[None, :]
        dd = np.sqrt(dx * dx + dy * dy)
        iu = np.triu_indices(p1.size, k=1)
        return dd[iu]

    def cdf_meandiff(d):
        d = np.sort(d)
        n = d.size
        lam = 1.0 / d.mean()
        emp = (np.arange(1, n + 1) - 0.5) / n
        fit = 1.0 - np.exp(-lam * d)
        return float(np.mean(np.abs(emp - fit)))

    print("A3. Alternative structures, tau=1, bins=5 / zero_to_max / abs_prop where applicable:")
    for label, dist_fn in (("radius-from-origin", radius_dist), ("L1 step", l1_dist),
                            ("all-pairs Euclidean", all_pairs_dist)):
        errs = [abs(expfit_meandiff(dist_fn(y, 1)) - ref) for y, ref in zip(frames, refs)]
        print(f"    {label:20s} max|err|={max(errs):.6f}")
    errs = [abs(cdf_meandiff(embed2_dist(np.asarray(y, dtype=float), 1)) - ref)
            for y, ref in zip(frames, refs)]
    print(f"    {'CDF meandiff':20s} max|err|={max(errs):.6f}")


def main():
    print("pycatch22 installed in this worktree:", HAVE_PYCATCH22)
    if not HAVE_PYCATCH22:
        print("ABSENT -- sections A0-A3 cannot run.")
        return
    section_a0_affine_invariance()
    print()
    section_a1_broad_sweep()
    print()
    section_a2_tau_pinned()
    print()
    section_a3_alt_structures()


if __name__ == "__main__":
    main()
