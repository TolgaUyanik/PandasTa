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

Result, stated in the companion receipt (`docs/C22EmbeddingDistMeasured.md`):
no FIXED bin count (34 distinct readings tried: 30 in the main grid, 4 more
in sA3, all now z-scored per step 1 above -- round 1 of review fixed a bug
where sA2/sA3 had skipped that step) reproduces the oracle, plateauing at a
max error of 1.0-3.9% (ddof=1) once z-scored correctly. A data-driven bin count gets much
closer: numpy's own `bins='auto'` convention (Freedman-Diaconis vs Sturges,
whichever is narrower -- a documented, non-GPL library default) reproduces
the oracle to float precision on 30 of 33 frames tried (7/8 tau-pinned, 23/25
diverse), with the 3 exceptions off by exactly one bin (max error 1.7%) --
not a structural miss, but not a "0 of N disagree" genuine match either (the
bar `c22_acf_first_min`'s sP sets). No variant tried clears that bar on every
frame. Gate A is UNRESOLVED and PandasTa issue #132 is closed as a measured
revert: no `pandas_ta` module, test or wiring entry was added for this
feature in this port, because shipping a column whose correctness could not
be checked on every frame tried would be exactly the "claim written before
it was measured" this repository's CLAUDE.md calls its dominant defect.
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


def zscore(y, ddof=1):
    """Step 1 of the definition. `candidate()` uses ddof=1; some sections
    below also report ddof=0 to size how much that choice alone moves a
    density reading."""
    y = np.asarray(y, dtype=float)
    return (y - y.mean()) / np.std(y, ddof=ddof)


def scott_bins(d):
    """Scott's normal-reference rule (bin WIDTH = 3.49*std*n^-1/3), the
    convention MATLAB's `histcounts`/`histogram('auto')` falls back to for
    non-integer data -- documented, public, non-GPL library behaviour."""
    n = d.size
    if n < 2:
        return 1
    std = np.std(d, ddof=1)
    span = d.max() - d.min()
    if std <= 0 or span <= 0:
        return 1
    width = 3.49 * std * n ** (-1.0 / 3.0)
    return max(1, int(np.ceil(span / width)))


def freedman_diaconis_bins(d):
    """Freedman-Diaconis rule (bin WIDTH = 2*IQR*n^-1/3)."""
    n = d.size
    if n < 2:
        return 1
    q75, q25 = np.percentile(d, [75, 25])
    iqr = q75 - q25
    span = d.max() - d.min()
    if iqr <= 0 or span <= 0:
        return 1
    width = 2.0 * iqr * n ** (-1.0 / 3.0)
    return max(1, int(np.ceil(span / width)))


def sqrt_bins(d):
    """`ceil(sqrt(n))`, the other common histogram-default rule."""
    return max(1, int(np.ceil(np.sqrt(d.size))))


def numpy_auto_bins(d):
    """numpy's own `bins='auto'` convention: `max(Freedman-Diaconis count,
    Sturges count)` -- i.e. whichever of the two gives the NARROWER bin
    width. This is numpy's documented library default (`np.histogram`
    with no explicit `bins`), distinct from plain Freedman-Diaconis
    alone (`freedman_diaconis_bins` above), which never falls back to
    Sturges when the FD width degenerates on small/skewed samples."""
    return len(np.histogram_bin_edges(d, bins="auto")) - 1


def build_a1_frames(rng):
    """25 mixed synthetic frames -- shared by sA1 and sA2b so both sections
    measure the identical frame set."""
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
    return frames


def build_a2_frames(rng):
    """8 strongly anti-persistent frames (tau=1 under every plausible
    first-zero convention) -- shared by sA2, sA2b and sA3."""
    frames = []
    for i in range(8):
        n = int(rng.integers(40, 90))
        y = ((-1.0) ** np.arange(n)) * (1.0 + 0.3 * rng.normal(size=n))
        frames.append(y)
    return frames


def expfit_meandiff(d, bins=5, edges="zero_to_max", metric="abs_prop"):
    """The candidate statistic: moment-matched exponential vs a histogram
    of `d`, compared by mean absolute difference -- of bin PROPORTIONS
    (`abs_prop`, this function's default and §A1's reading), raw COUNTS
    (`abs_count`) or DENSITY (`abs_density`). Affine invariance of the
    oracle's output (section A0) does NOT single out one of the three:
    `d` is computed from an already-z-scored series, so it is invariant
    to the original input's scale before any of the three ever runs.
    §A2 tests all three empirically instead of assuming one."""
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
    zero_to_max, abs_prop -- the house default reading (5 bins, as
    `c22_ami2` uses), checked against the oracle."""
    import pycatch22

    fn = pycatch22.CO_Embed2_Dist_tau_d_expfit_meandiff
    rng = np.random.default_rng(1)
    frames = build_a1_frames(rng)

    errs, refs = [], []
    for y in frames:
        ref = fn(y.tolist())
        refs.append(ref)
        val, _tau = candidate(y)
        if not (np.isnan(val) or np.isnan(ref)):
            errs.append(abs(val - ref))
    print("A1. Broad sweep, 25 mixed frames, candidate(bins=5, zero_to_max, abs_prop):")
    print(f"    n={len(errs)}  max|err|={max(errs):.6f}  mean|err|={np.mean(errs):.6f}")
    print(f"    oracle's own range on these 25 frames: {min(refs):.6f} .. {max(refs):.6f}")

    # Cross-check: does §A2's best reading (narrow, tau-pinned frames)
    # also hold up here, on diverse frames with the candidate's own
    # (not pinned) tau? If it doesn't generalise, that is further
    # evidence against it rather than for it.
    errs2 = []
    for y, ref in zip(frames, refs):
        val, _tau = candidate(y, bins=10, edges="min_to_max", metric="abs_density")
        if not (np.isnan(val) or np.isnan(ref)):
            errs2.append(abs(val - ref))
    print("    same 25 frames, candidate(bins=10, min_to_max, abs_density) -- "
          "§A2's own best reading, candidate's own tau:")
    print(f"    n={len(errs2)}  max|err|={max(errs2):.6f}  mean|err|={np.mean(errs2):.6f}")


def section_a2_tau_pinned():
    """8 strongly anti-persistent frames (acf(1) approx -0.9 by
    construction: alternating sign, so ANY first-zero convention reads
    tau=1 -- this isolates the histogram/fit step from the tau rule."""
    import pycatch22

    fn = pycatch22.CO_Embed2_Dist_tau_d_expfit_meandiff
    rng = np.random.default_rng(7)
    frames = build_a2_frames(rng)
    refs = [fn(y.tolist()) for y in frames]

    acf1 = []
    for y in frames:
        yo = y - y.mean()
        acf1.append(float(np.sum(yo[:-1] * yo[1:]) / np.sum(yo * yo)))
    print("A2. Tau pinned to 1 by construction (acf(1) of the 8 frames):")
    print("    " + ", ".join(f"{v:.3f}" for v in acf1))
    print(f"    oracle's own range on these 8 frames: {min(refs):.6f} .. {max(refs):.6f}")

    # Step 1 of the definition (z-score) applies BEFORE embed2_dist, same
    # as candidate() -- this grid was previously computed on the raw
    # frame, which mis-scales the density metric (CRITICAL, round 1).
    zframes = [zscore(y, ddof=1) for y in frames]

    print("    bins  edges        metric       max|err|  (z-scored, ddof=1)")
    best = None
    for bins in (3, 5, 10, 20, 40):
        for edges in ("zero_to_max", "min_to_max"):
            for metric in ("abs_prop", "abs_count", "abs_density"):
                errs = []
                for z, ref in zip(zframes, refs):
                    d = embed2_dist(z, 1)
                    val = expfit_meandiff(d, bins=bins, edges=edges, metric=metric)
                    errs.append(abs(val - ref))
                m = max(errs)
                print(f"    {bins:4d}  {edges:11s}  {metric:11s}  {m:.6f}")
                if best is None or m < best[0]:
                    best = (m, bins, edges, metric)
    print(f"    best: bins={best[1]} edges={best[2]} metric={best[3]} max|err|={best[0]:.6f}")

    # Per-frame, how much did the round-1 z-score bug actually move the
    # winning config's error, frame by frame? The metric VALUE scales by
    # exactly that frame's own sigma (an algebraic fact: d_z = d_raw/sigma,
    # histogram bin membership is unchanged by a uniform rescale of both
    # `d` and its own min/max edges, so density and its exponential fit
    # both scale by 1/sigma -- see expfit_meandiff). But ERROR is
    # |value - ref| against a FIXED oracle reference, so a ~sigma move in
    # value does NOT translate into a uniform shift in error -- it can
    # swing in either direction by any amount depending which side of
    # `ref` the raw value already sat on. Printed, not asserted:
    print("    per-frame value/error under the z-score fix, bins=10/min_to_max/abs_density:")
    for i, (y, ref) in enumerate(zip(frames, refs)):
        sigma = np.std(y, ddof=1)
        d_raw = embed2_dist(np.asarray(y, dtype=float), 1)
        val_raw = expfit_meandiff(d_raw, bins=10, edges="min_to_max", metric="abs_density")
        err_raw = abs(val_raw - ref)
        d_z = embed2_dist(zscore(y, ddof=1), 1)
        val_z = expfit_meandiff(d_z, bins=10, edges="min_to_max", metric="abs_density")
        err_z = abs(val_z - ref)
        pct = "n/a" if err_raw == 0 else f"{(err_z - err_raw) / err_raw * 100:+.1f}%"
        print(f"      frame {i}: sigma={sigma:.4f}  val_raw={val_raw:.6f}  val_z={val_z:.6f}"
              f"  (val_z/val_raw={val_z / val_raw:.4f})  err_raw={err_raw:.6f}  err_z={err_z:.6f}"
              f"  err_change={pct}")

    # How much does ddof alone move the winning (density) reading? At
    # n=40..90, std(ddof=0) vs std(ddof=1) differ by sqrt(n/(n-1)) ~
    # 0.6-1.3%; that is a statement about `std`, not about the resulting
    # error (see the per-frame table above: value changes don't translate
    # into proportional error changes against a fixed reference).
    zframes0 = [zscore(y, ddof=0) for y in frames]
    errs0 = []
    for z, ref in zip(zframes0, refs):
        d = embed2_dist(z, 1)
        val = expfit_meandiff(d, bins=best[1], edges=best[2], metric=best[3])
        errs0.append(abs(val - ref))
    print(f"    same best config, ddof=0 z-score instead: max|err|={max(errs0):.6f}"
          f" (ddof=1 was {best[0]:.6f})")

    # The winner above (min_to_max / abs_density) is the closest reading
    # found. Sweep its bin count finely to check whether the gap is just
    # "wrong bin count" (would converge to ~0 somewhere in this range) or
    # a genuine residual (stays bounded away from 0 everywhere).
    print("    fine bin sweep of the winner (min_to_max, abs_density), bins 4..24, ddof=1:")
    fine_max, fine_mean = [], []
    for bins in range(4, 25):
        errs = []
        for z, ref in zip(zframes, refs):
            d = embed2_dist(z, 1)
            val = expfit_meandiff(d, bins=bins, edges="min_to_max", metric="abs_density")
            errs.append(abs(val - ref))
        fine_max.append(max(errs))
        fine_mean.append(float(np.mean(errs)))
    print(f"    bins 4..24: max|err| ranges {min(fine_max):.6f} .. {max(fine_max):.6f}"
          f" (best at bins={4 + int(np.argmin(fine_max))})")
    print(f"    bins 4..24: mean|err| ranges {min(fine_mean):.6f} .. {max(fine_mean):.6f}")

    print("    same fine sweep, ddof=0 z-score instead:")
    fine_max0, fine_mean0 = [], []
    for bins in range(4, 25):
        errs = []
        for z, ref in zip(zframes0, refs):
            d = embed2_dist(z, 1)
            val = expfit_meandiff(d, bins=bins, edges="min_to_max", metric="abs_density")
            errs.append(abs(val - ref))
        fine_max0.append(max(errs))
        fine_mean0.append(float(np.mean(errs)))
    print(f"    bins 4..24: max|err| ranges {min(fine_max0):.6f} .. {max(fine_max0):.6f}"
          f" (best at bins={4 + int(np.argmin(fine_max0))})")
    print(f"    bins 4..24: mean|err| ranges {min(fine_mean0):.6f} .. {max(fine_mean0):.6f}")


def section_a2b_auto_bin_rules():
    """The data-driven bin-count family the fixed grid above never tried
    (MAJOR, round 1): Scott's normal-reference rule, Freedman-Diaconis,
    and ceil(sqrt(n)) -- the convention a histogram call inherits as its
    library default, documented and non-GPL. Crossed with both edge
    conventions and all three metrics, on z-scored (ddof=1) `d`, on both
    the 8 tau-pinned frames (sA2) and sA1's 25 diverse frames (candidate's
    own tau there, since nothing pins it on that set)."""
    import pycatch22

    fn = pycatch22.CO_Embed2_Dist_tau_d_expfit_meandiff
    rules = (("scott", scott_bins), ("freedman_diaconis", freedman_diaconis_bins),
              ("sqrt", sqrt_bins))

    def run(frames, tau_fixed, label):
        refs = [fn(y.tolist()) for y in frames]
        zframes = [zscore(y, ddof=1) for y in frames]
        print(f"    {label}:")
        best = None
        for rule_name, rule_fn in rules:
            for edges in ("zero_to_max", "min_to_max"):
                for metric in ("abs_prop", "abs_count", "abs_density"):
                    errs = []
                    bins_used = []
                    for z, ref in zip(zframes, refs):
                        tau = tau_fixed if tau_fixed is not None else acf_first_zero(z)
                        d = embed2_dist(z, tau)
                        nb = rule_fn(d)
                        bins_used.append(nb)
                        val = expfit_meandiff(d, bins=nb, edges=edges, metric=metric)
                        errs.append(abs(val - ref))
                    m = max(errs)
                    print(f"      {rule_name:18s} {edges:11s} {metric:11s} max|err|={m:.6f}"
                          f" bins={bins_used}")
                    if best is None or m < best[0]:
                        best = (m, rule_name, edges, metric)
        print(f"      best auto-bin config on {label}: {best[1]}/{best[2]}/{best[3]}"
              f" max|err|={best[0]:.6f}")

    rng7 = np.random.default_rng(7)
    run(build_a2_frames(rng7), tau_fixed=1, label="8 tau-pinned frames (sA2)")
    rng1 = np.random.default_rng(1)
    run(build_a1_frames(rng1), tau_fixed=None, label="25 diverse frames (sA1)")

    # Per-frame optimal bin count for the density metric (min_to_max
    # edges, tau=1): does it track n, or either auto-bin rule's count?
    print("    per-frame optimal bin count for abs_density (min_to_max, tau=1), sA2 frames:")
    rng7b = np.random.default_rng(7)
    frames = build_a2_frames(rng7b)
    refs = [fn(y.tolist()) for y in frames]
    zframes = [zscore(y, ddof=1) for y in frames]
    for i, (z, ref) in enumerate(zip(zframes, refs)):
        d = embed2_dist(z, 1)
        best_bins, best_err = None, None
        for b in range(2, 41):
            val = expfit_meandiff(d, bins=b, edges="min_to_max", metric="abs_density")
            err = abs(val - ref)
            if best_err is None or err < best_err:
                best_err, best_bins = err, b
        print(f"      frame {i}: n(d)={d.size:3d}  optimal_bins={best_bins:2d}  err={best_err:.6f}"
              f"  scott={scott_bins(d)}  fd={freedman_diaconis_bins(d)}  sqrt={sqrt_bins(d)}")

    # The per-frame optimal bin counts above don't track any of the three
    # single-rule families cleanly. numpy's actual `bins='auto'` tie-break
    # (max of FD and Sturges counts, not FD alone) was not in that family
    # and is tried here as a fourth, equally public, equally non-GPL
    # reading -- min_to_max edges, abs_density, z-scored (ddof=1) `d`.
    print("    numpy bins='auto' (max(FD, Sturges) by width), min_to_max, abs_density, ddof=1:")

    def run_numpy_auto(frames, tau_fixed, label):
        refs = [fn(y.tolist()) for y in frames]
        zframes = [zscore(y, ddof=1) for y in frames]
        errs, exact_errs = [], []
        for i, (z, ref) in enumerate(zip(zframes, refs)):
            tau = tau_fixed if tau_fixed is not None else acf_first_zero(z)
            d = embed2_dist(z, tau)
            nb = numpy_auto_bins(d)
            val = expfit_meandiff(d, bins=nb, edges="min_to_max", metric="abs_density")
            err = abs(val - ref)
            errs.append(err)
            if err < 1e-4:
                exact_errs.append(err)
            else:
                # What bin count WOULD have been needed here? (brute force,
                # same range as the sA2 per-frame optimal-bin search above.)
                best_bins, best_err = None, None
                for b in range(2, 80):
                    v = expfit_meandiff(d, bins=b, edges="min_to_max", metric="abs_density")
                    e = abs(v - ref)
                    if best_err is None or e < best_err:
                        best_err, best_bins = e, b
                print(f"      {label} frame {i}: n(d)={d.size:3d} bins={nb:2d} err={err:.6f}"
                      f" (not float-precision; needed bins={best_bins}, err there={best_err:.6f})")
        print(f"      {label}: {len(exact_errs)}/{len(frames)} frames match to float precision (<1e-4);"
              f" of those, err ranges {min(exact_errs):.2e} .. {max(exact_errs):.2e};"
              f" overall max|err|={max(errs):.6f} mean|err|={np.mean(errs):.6f}")

    rng7c = np.random.default_rng(7)
    run_numpy_auto(build_a2_frames(rng7c), tau_fixed=1, label="8 tau-pinned (sA2)")
    rng1b = np.random.default_rng(1)
    run_numpy_auto(build_a1_frames(rng1b), tau_fixed=None, label="25 diverse (sA1)")


def section_a3_alt_structures():
    """Structural alternatives to the consecutive-Euclidean-distance,
    histogram-proportion reading: radius-from-origin distance, L1
    distance, all-PAIRS Euclidean distance (not just temporally
    consecutive pairs), and a CDF-based (bin-free) meandiff -- all on the
    same tau-pinned frames as A2."""
    import pycatch22

    fn = pycatch22.CO_Embed2_Dist_tau_d_expfit_meandiff
    rng = np.random.default_rng(7)
    frames = build_a2_frames(rng)
    refs = [fn(y.tolist()) for y in frames]
    zframes = [zscore(y, ddof=1) for y in frames]

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

    print("A3. Alternative structures, z-scored, tau=1, bins=5 / zero_to_max / abs_prop where applicable:")
    for label, dist_fn in (("radius-from-origin", radius_dist), ("L1 step", l1_dist),
                            ("all-pairs Euclidean", all_pairs_dist)):
        errs = [abs(expfit_meandiff(dist_fn(z, 1)) - ref) for z, ref in zip(zframes, refs)]
        print(f"    {label:20s} max|err|={max(errs):.6f}")
    errs = [abs(cdf_meandiff(embed2_dist(z, 1)) - ref)
            for z, ref in zip(zframes, refs)]
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
    section_a2b_auto_bin_rules()
    print()
    section_a3_alt_structures()


if __name__ == "__main__":
    main()
