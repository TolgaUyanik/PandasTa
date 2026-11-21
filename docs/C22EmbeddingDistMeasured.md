# `c22_embedding_dist` — measured and reverted

PandasTa issue **#132** (C22-EMBEDDING-DIST), attempted 2026-11-21 on branch
`issue-132-c22-embedding-dist`. **No `pandas_ta` module, test or wiring entry
was added.** Gate A could not be cleared honestly, so nothing ships; this
file is the receipt.

| | |
|---|---|
| candidate | catch22 (Lubba et al. 2019, *Data Min. Knowl. Disc.* 33:1821), feature `CO_Embed2_Dist_tau_d_expfit_meandiff` — the hctsa operation `CO_Embed2_Dist(y,'tau')`, exponential-fit misfit of consecutive distances in a 2-D delay embedding — proposed on the last 100 daily simple returns |
| harness | `docs/measure_c22_embedding_dist.py` (sections A0-A3; a bare run imports `pycatch22` 1.0.2 when present in the environment, used strictly as a BLACK-BOX ORACLE, never read as source, never imported outside this one `docs/` script) |
| Gate A | **UNRESOLVED.** 25-frame broad sweep: max \|err\| 1.245120 against the best-effort candidate (§A1). Isolating the delay parameter (8 frames built so `tau = 1` under every plausible convention, §A2), z-scored correctly: best FIXED bin count of 30 variants max \|err\| 0.023518 (bins=10, min-to-max edges, density); fine sweep of that reading plateaus at 0.010-0.039. A data-driven bin count gets far closer — numpy's `bins='auto'` convention reproduces the oracle to float precision on 30 of 33 frames (7/8 + 23/25), but 3 frames stay off by exactly one bin, max \|err\| 0.017442 (§A2b). Four alternative structural readings (§A3) all stayed at max \|err\| > 0.19 (range 0.1995-0.3236). No reading tried reproduces the oracle on every frame. |
| Gate B/C/D | not attempted — no module exists to test |
| Gate E | not applicable — nothing shipped |
| Gate F | whole suites, launcher's clean worktrees — see §6 |
| outcome | **measured revert** per issue #132: "a measured revert closes this exactly as well as a ship" |

Every number below is `python docs/measure_c22_embedding_dist.py`'s own output
on this machine (numpy 1.26.4, pandas 2.3.3, Python 3.11, `pycatch22` 1.0.2
present in this worktree). Round 1 of review found a bug in this receipt's
first draft — §A2/§A3 fed the RAW frame into `embed2_dist` instead of the
z-scored one step 1 of the definition requires, mis-scaling the density
metric by the frame's own σ (≈4%) — and a cheap untried family (data-driven
bin counts). Both are fixed below; every number in §3/§4 was re-measured
after the fix, not patched by hand.

---

## 0. What was tried, and why it stopped here

The issue's own instruction is narrow: "port from the paper's and hctsa's
definitions, never from that code" (the reference, `pycatch22` 1.0.2, is
GPL-3.0; this fork is MIT). The paper and hctsa's published operation
description settle the SHAPE of the feature and nothing more:

1. z-score the series (step 1 — the harness's §A2/§A3 skipped this in round
   1 of review and both sections were re-measured with it applied; see the
   note above §1 and the CRITICAL-fix note under §3);
2. pick a delay `tau` from the series' own autocorrelation (hctsa's
   `CO_FirstZero(y,'ac')` convention: the first lag whose autocorrelation is
   non-positive, falling back near `N/10` when none is found before then);
3. build the 2-D delay embedding `(y[i], y[i+tau])`;
4. take the Euclidean distance between every pair of temporally
   CONSECUTIVE embedded points;
5. fit an exponential distribution to those distances by maximum
   likelihood (`lambda = 1 / mean(d)`);
6. report the mean difference between the empirical distribution of `d`
   and the fitted one.

What is **not** settled by that paragraph, and is not published anywhere
non-GPL: how many histogram bins, what their edges span, whether the
comparison is of bin PROPORTIONS, densities, or raw counts, and whether
"distribution" even means a histogram rather than a CDF read. Those are
exactly the kind of details this fork's existing catch22 ports (`c22_ami2`,
`c22_acf_first_min`) settled by fitting several candidate readings against
`pycatch22` used as a BLACK-BOX ORACLE — never reading its source, only
calling it and comparing outputs, the same thing §A0-§A3 below do. For this
feature that process did not converge on every frame — not for lack of
trying a data-driven bin count (§A2b), which gets close but not all the way.

## 1. §A0 — the oracle's own output is affine-invariant

```
A0. Affine invariance of the oracle (base=0.136875651153)
    x7.3: 0.136875651153  |diff|=2.78e-17
    +50: 0.136875651153  |diff|=5.55e-17
    x7.3+50: 0.136875651153  |diff|=5.55e-17
```

Scaling or shifting the input by an affine map leaves the reference's
output unchanged to rounding. ⚠ **This does NOT, on its own, rule out a
raw density comparison.** The candidate z-scores `y` before computing
`tau`, the embedding or `d` (step 1 of §0), so `d` is already invariant
to an affine map of the ORIGINAL input before any final metric runs on
it — proportion, count and density are then all equally invariant
downstream of that z-score, and this test cannot distinguish between
them. (An earlier draft of this receipt argued density was "ruled out
analytically" by this invariance and dropped it from §A2's search; that
argument was wrong for exactly the reason above. Density is carried
into §A2 below and tested empirically like everything else — and turns
out to be the closest reading found, see §3.)

## 2. §A1 — the best-effort candidate against 25 mixed synthetic frames

The single house-default reading (5 bins, as `c22_ami2` uses) of the
six-step paragraph above — `tau` from `CO_FirstZero('ac')` capped near
`N/10`, 5 bins spanning `[0, max(d)]`, mean absolute difference of bin
PROPORTIONS — checked against the oracle on 25 synthetic frames (iid
normal, a random walk, a noisy 17-bar sine, an AR(1) at phi 0.7, and a
Student-t(3) path, five each, lengths 60-300):

```
A1. Broad sweep, 25 mixed frames, candidate(bins=5, zero_to_max, abs_prop):
    n=25  max|err|=1.245120  mean|err|=0.308518
    oracle's own range on these 25 frames: 0.029989 .. 1.358727
```

A max error of 1.245120 against an oracle range of 0.029989 to 1.358727
means the candidate is not a loose approximation, it is reading a
different quantity. (`candidate()` already z-scores correctly — this
section's numbers are unaffected by the §A2/§A3 bug fixed in this round.)

**Cross-check, after §3 found its own best FIXED-bin reading:** does the
closest fixed config found on the narrow tau-pinned frames (§3 below — 10
bins, `min_to_max` edges, density comparison) generalise to these 25
diverse frames, using the candidate's own (not pinned) `tau`?

```
    same 25 frames, candidate(bins=10, min_to_max, abs_density) -- §A2's own best reading, candidate's own tau:
    n=25  max|err|=0.062813  mean|err|=0.014178
```

It does not fall apart on the diverse set, but the max error is roughly
2.7x relative to §3's corrected best fixed reading (0.063 vs 0.024,
both z-scored the same way) rather than improving — so the near-miss in
§3 is not an artefact of those 8 frames being unusual; it generalises in
the wrong direction. It still never approaches the oracle's own float
precision on either test set with a FIXED bin count.

## 3. §A2 — isolating the delay parameter, with the z-score bug fixed

If `tau` were the only wrong piece, pinning it independently of the
candidate's own `CO_FirstZero` logic should close most of the gap. Eight
frames were built so that `tau = 1` under EVERY plausible first-zero
convention: alternating sign (`(-1)**i * (1 + noise)`), whose lag-1
autocorrelation is strongly negative by construction:

```
A2. Tau pinned to 1 by construction (acf(1) of the 8 frames):
    -0.920, -0.888, -0.923, -0.909, -0.915, -0.903, -0.877, -0.930
    oracle's own range on these 8 frames: 0.297274 .. 0.422275
```

**Round 1 of review (CRITICAL) found that `section_a2_tau_pinned` and
`section_a3_alt_structures` fed the RAW frame into `embed2_dist`, skipping
step 1 of the definition (z-score) that `candidate()` applies and this
receipt's own §0 states. `abs_prop` and `abs_count` are provably
scale-invariant (histogram counts are identical whether `d` or `edges`
are scaled by the same constant, since bin membership doesn't change) and
unaffected; `abs_density` is not — scaling `d` by a constant `c` scales
the `abs_density` VALUE by `1/c` exactly. That does **not** mean the ERROR
against the fixed oracle reference moves by the same ≈4-5% that `σ`
implies — error is `|value − ref|` with `ref` fixed, so a move in `value`
can shrink, grow, or flip the sign of `value − ref` depending on which
side of `ref` the raw value already sat on. Every number below, including
the per-frame table, is printed by the harness itself (nothing here is
hand-derived), which z-scores (ddof=1, matching `candidate()`) before
computing `d`:**

30 histogram variants (bins in `{3, 5, 10, 20, 40}` x edges `{zero-to-max,
min-to-max}` x metric `{proportion, count, density}`), `tau` fixed at 1,
against the same 8 frames' oracle values:

```
    bins  edges        metric       max|err|  (z-scored, ddof=1)
       3  zero_to_max  abs_prop     0.094732
       3  zero_to_max  abs_count    27.722673
       3  zero_to_max  abs_density  0.148191
       3  min_to_max   abs_prop     0.171363
       3  min_to_max   abs_count    22.834991
       3  min_to_max   abs_density  0.032341
       5  zero_to_max  abs_prop     0.203956
       5  zero_to_max  abs_count    18.384777
       5  zero_to_max  abs_density  0.117797
       5  min_to_max   abs_prop     0.271793
       5  min_to_max   abs_count    13.071413
       5  min_to_max   abs_density  0.030961
      10  zero_to_max  abs_prop     0.298427
      10  zero_to_max  abs_count    9.491685
      10  zero_to_max  abs_density  0.079717
      10  min_to_max   abs_prop     0.347047
      10  min_to_max   abs_count    6.553204
      10  min_to_max   abs_density  0.023518
      20  zero_to_max  abs_prop     0.360344
      20  zero_to_max  abs_count    4.717885
      20  zero_to_max  abs_density  0.076789
      20  min_to_max   abs_prop     0.382255
      20  min_to_max   abs_count    3.241805
      20  min_to_max   abs_density  0.033505
      40  zero_to_max  abs_prop     0.390094
      40  zero_to_max  abs_count    2.270201
      40  zero_to_max  abs_density  0.063234
      40  min_to_max   abs_prop     0.400591
      40  min_to_max   abs_count    1.473728
      40  min_to_max   abs_density  0.064561
    best: bins=10 edges=min_to_max metric=abs_density max|err|=0.023518
    per-frame value/error under the z-score fix, bins=10/min_to_max/abs_density:
      frame 0: sigma=0.9835  val_raw=0.349083  val_z=0.343308  (val_z/val_raw=0.9835)  err_raw=0.017817  err_z=0.012042  err_change=-32.4%
      frame 1: sigma=1.0034  val_raw=0.361803  val_z=0.363029  (val_z/val_raw=1.0034)  err_raw=0.022292  err_z=0.023518  err_change=+5.5%
      frame 2: sigma=1.0455  val_raw=0.339456  val_z=0.354889  (val_z/val_raw=1.0455)  err_raw=0.022175  err_z=0.006742  err_change=-69.6%
      frame 3: sigma=1.0082  val_raw=0.294852  val_z=0.297274  (val_z/val_raw=1.0082)  err_raw=0.002422  err_z=0.000000  err_change=-100.0%
      frame 4: sigma=1.0514  val_raw=0.381721  val_z=0.401351  (val_z/val_raw=1.0514)  err_raw=0.028614  err_z=0.008985  err_change=-68.6%
      frame 5: sigma=1.0122  val_raw=0.363699  val_z=0.368119  (val_z/val_raw=1.0122)  err_raw=0.000447  err_z=0.004867  err_change=+989.1%
      frame 6: sigma=0.9584  val_raw=0.440583  val_z=0.422248  (val_z/val_raw=0.9584)  err_raw=0.018309  err_z=0.000027  err_change=-99.9%
      frame 7: sigma=0.9517  val_raw=0.359872  val_z=0.342479  (val_z/val_raw=0.9517)  err_raw=0.018954  err_z=0.001561  err_change=-91.8%
```

`abs_prop` and `abs_count` are provably unaffected by the z-score bug (both
are affine-invariant by construction, per the per-bin derivation above).
Only the `abs_density` column moved — the grid's max moved from the
unscaled draft's 0.028614 down to 0.023518 at the same bins=10. The
per-frame table above confirms `val_z/val_raw` equals each frame's own
`sigma` to 4 decimals (the algebraic scaling fact), while `err_change`
ranges from −100.0% (frame 3, which lands exactly on the oracle after
z-scoring) to +989.1% (frame 5, whose raw error happened to sit extremely
close to zero before the fix) — not a uniform ≈4% shift in either value
or error. An earlier draft of this paragraph claimed the two were "the
same order," which does not survive this per-frame check and is
withdrawn. The winner config itself (bins=10,
min-to-max, density) is unchanged.

**ddof of the z-score also moves the winning reading, by more than its
own ~0.6-1.3% std shift would suggest — same reason as above:**

```
    same best config, ddof=0 z-score instead: max|err|=0.020952 (ddof=1 was 0.023518)
```

Switching ddof moves `std` by only ≈0.6-1.3% at n=40-90 (as the MAJOR
finding predicted), but that moves this config's ERROR by 10.9%
(0.023518 → 0.020952) — the same value-vs-fixed-reference sensitivity
as the z-score fix itself, not a contradiction of the 0.6-1.3% std
prediction, which was about `std`, not about this derived error.
`candidate()` uses ddof=1, so that is the number carried forward.

The density reading is the closest FIXED-bin reading found, so its bin
count was swept finely (4 to 24, `min_to_max` edges) to check whether the
10-bin result above was a lucky stopping point that would reach ~0 nearby:

```
    fine bin sweep of the winner (min_to_max, abs_density), bins 4..24, ddof=1:
    bins 4..24: max|err| ranges 0.010134 .. 0.039181 (best at bins=8)
    bins 4..24: mean|err| ranges 0.002606 .. 0.021705

    same fine sweep, ddof=0 z-score instead:
    bins 4..24: max|err| ranges 0.009570 .. 0.036505 (best at bins=8)
    bins 4..24: mean|err| ranges 0.004747 .. 0.018953
```

No FIXED bin count in 4..24 reaches the oracle's own float precision under
either ddof, and the best-bins location (8) does not move between ddof=0
and ddof=1. The fixed-bin plateau is real at 1.0-3.9%, smaller than round
1's unscaled 2.0-5.4% but still a genuine, persistent residual — **not**
closed by correcting the z-score bug alone.

### §A2b — the data-driven bin count family (MAJOR, round 1)

The fixed-count grid above never tried a bin count that VARIES with the
data, which is exactly what a histogram call inherits as its library
default and is the family the "no fixed count fits" result points at. Three
named, documented, non-GPL rules (Scott's normal-reference rule, Freedman-
Diaconis, `ceil(sqrt(n))`), crossed with both edge conventions and all
three metrics, z-scored (ddof=1), on both the 8 tau-pinned frames and §A1's
25 diverse frames (candidate's own tau there):

```
    8 tau-pinned frames (sA2):
      scott              zero_to_max abs_prop    max|err|=0.203956 bins=[7, 6, 5, 7, 5, 6, 5, 6]
      scott              zero_to_max abs_count   max|err|=15.117881 bins=[7, 6, 5, 7, 5, 6, 5, 6]
      scott              zero_to_max abs_density max|err|=0.117797 bins=[7, 6, 5, 7, 5, 6, 5, 6]
      scott              min_to_max  abs_prop    max|err|=0.271793 bins=[7, 6, 5, 7, 5, 6, 5, 6]
      scott              min_to_max  abs_count   max|err|=9.397217 bins=[7, 6, 5, 7, 5, 6, 5, 6]
      scott              min_to_max  abs_density max|err|=0.030961 bins=[7, 6, 5, 7, 5, 6, 5, 6]
      freedman_diaconis  zero_to_max abs_prop    max|err|=0.215914 bins=[8, 8, 7, 11, 6, 7, 6, 9]
      freedman_diaconis  zero_to_max abs_count   max|err|=13.120815 bins=[8, 8, 7, 11, 6, 7, 6, 9]
      freedman_diaconis  zero_to_max abs_density max|err|=0.079806 bins=[8, 8, 7, 11, 6, 7, 6, 9]
      freedman_diaconis  min_to_max  abs_prop    max|err|=0.296882 bins=[8, 8, 7, 11, 6, 7, 6, 9]
      freedman_diaconis  min_to_max  abs_count   max|err|=7.761850 bins=[8, 8, 7, 11, 6, 7, 6, 9]
      freedman_diaconis  min_to_max  abs_density max|err|=0.030997 bins=[8, 8, 7, 11, 6, 7, 6, 9]
      sqrt               zero_to_max abs_prop    max|err|=0.274123 bins=[10, 9, 8, 10, 9, 9, 8, 9]
      sqrt               zero_to_max abs_count   max|err|=9.506353 bins=[10, 9, 8, 10, 9, 9, 8, 9]
      sqrt               zero_to_max abs_density max|err|=0.076854 bins=[10, 9, 8, 10, 9, 9, 8, 9]
      sqrt               min_to_max  abs_prop    max|err|=0.328237 bins=[10, 9, 8, 10, 9, 9, 8, 9]
      sqrt               min_to_max  abs_count   max|err|=6.553204 bins=[10, 9, 8, 10, 9, 9, 8, 9]
      sqrt               min_to_max  abs_density max|err|=0.017699 bins=[10, 9, 8, 10, 9, 9, 8, 9]
      best auto-bin config on 8 tau-pinned frames (sA2): sqrt/min_to_max/abs_density max|err|=0.017699
    25 diverse frames (sA1):
      ... (18 rows of the same scott/freedman_diaconis/sqrt x edges x metric grid, elided here -- same structure as above, run on sA1's 25 frames)
      best auto-bin config on 25 diverse frames (sA1): freedman_diaconis/min_to_max/abs_density max|err|=0.061574
```

None of these three single rules alone reproduces the oracle to float
precision — `sqrt`/min_to_max/density is a modest improvement over the
best FIXED count on the 8 tau-pinned frames (0.0177 vs 0.0235) and
Freedman-Diaconis alone is barely better than the fixed-10 cross-check
reading on the 25 diverse frames (0.0616 vs 0.0628) — not a structural
win either way.

**But per-frame, an EXACT bin count exists.** Brute-forcing every bin
count 2-40 against each of the 8 tau-pinned frames individually:

```
    per-frame optimal bin count for abs_density (min_to_max, tau=1), sA2 frames:
      frame 0: n(d)= 85  optimal_bins= 8  err=0.000000  scott=7  fd=8  sqrt=10
      frame 1: n(d)= 69  optimal_bins= 8  err=0.000000  scott=6  fd=8  sqrt=9
      frame 2: n(d)= 52  optimal_bins= 7  err=0.000000  scott=5  fd=7  sqrt=8
      frame 3: n(d)= 83  optimal_bins=10  err=0.000000  scott=7  fd=11  sqrt=10
      frame 4: n(d)= 67  optimal_bins= 8  err=0.000000  scott=5  fd=6  sqrt=9
      frame 5: n(d)= 75  optimal_bins= 8  err=0.000000  scott=6  fd=7  sqrt=9
      frame 6: n(d)= 56  optimal_bins= 7  err=0.000000  scott=5  fd=6  sqrt=8
      frame 7: n(d)= 71  optimal_bins= 9  err=0.000000  scott=6  fd=9  sqrt=9
```

EVERY one of the 8 frames has SOME bin count that reproduces the oracle to
float precision (err rounds to 0.000000 at 6 decimals). None of the three
single named rules tracks that per-frame optimum on its own — but `fd`
(Freedman-Diaconis alone) comes close on most rows. That pointed at
numpy's actual `bins='auto'` convention, which is NOT plain
Freedman-Diaconis: it is `max(Freedman-Diaconis count, Sturges count)` —
whichever rule gives the NARROWER bin width, falling back to Sturges when
FD's width degenerates. Trying that (still z-scored, ddof=1, min_to_max,
density):

```
    numpy bins='auto' (max(FD, Sturges) by width), min_to_max, abs_density, ddof=1:
      8 tau-pinned (sA2) frame 3: n(d)= 83 bins=11 err=0.006103 (not float-precision; needed bins=10, err there=0.000000)
      8 tau-pinned (sA2): 7/8 frames match to float precision (<1e-4); of those, err ranges 6.11e-09 .. 8.45e-08; overall max|err|=0.006103 mean|err|=0.000763
      25 diverse (sA1) frame 4: n(d)=287 bins=36 err=0.000544 (not float-precision; needed bins=35, err there=0.000000)
      25 diverse (sA1) frame 18: n(d)=206 bins=10 err=0.017442 (not float-precision; needed bins=9, err there=0.000000)
      25 diverse (sA1): 23/25 frames match to float precision (<1e-4); of those, err ranges 1.46e-10 .. 2.37e-07; overall max|err|=0.017442 mean|err|=0.000719
```

**This is the closest reading found by far: 30 of 33 frames (7/8 + 23/25)
reproduce the oracle to float precision** (errors 6.11e-09 to 2.37e-07 on
the frames that match, the same order as §A0's own rounding noise) under
`z-score(ddof=1) → tau(pinned or CO_FirstZero) → embed → consecutive
Euclidean distance → min-to-max edges → bins=max(FD,Sturges) → density →
mean|actual−fit|`. The 3 exceptions are each off by EXACTLY one bin (frame
3: 11 vs the needed 10; sA1 frame 4: 36 vs 35; sA1 frame 18: 10 vs the
needed 9 — all three "needed" counts above are the harness's own brute-force
search over bins 2-79 at each mismatched frame, printed above, not
asserted), not by a wrong structure — the kind of discrepancy a slightly
different percentile-interpolation or tie-break convention in the
oracle's own (GPL, unread) FD/Sturges implementation would produce.

**Restating the "persistent residual" conclusion from round 1, now that it
is measured rather than assumed:** the FIXED-bin plateau (1.0-3.9% even
after the z-score fix) is real, but it is a property of FIXED bins, not of
the feature being unrecoverable — a DATA-DRIVEN bin count very nearly
closes it (30/33 exact, worst case 1.7%). That is far closer than "no
reading tried reproduces the oracle" implied in round 1's framing, and it
is NOT a clean pass either: 3 of 33 frames stay off by one bin under the
one public auto-bin tie-break tried, and the issue explicitly forbids
reading the GPL source that would settle which exact tie-break the oracle
uses. Gate A's bar, per this fork's own precedent (`c22_acf_first_min`'s
§P: 0 of 8,400 windows disagreeing), is "0 of N disagree," not "30 of 33."
This reading does not clear that bar, so the revert stands — but on a far
narrower, now fully measured, residual than round 1 reported.

## 4. §A3 — alternative structural readings

Four more readings of "distance in the embedding", same 8 tau-pinned
frames, now also z-scored (round 1's CRITICAL fix applies here too):

```
A3. Alternative structures, z-scored, tau=1, bins=5 / zero_to_max / abs_prop where applicable:
    radius-from-origin   max|err|=0.199525
    L1 step              max|err|=0.203670
    all-pairs Euclidean  max|err|=0.323581
    CDF meandiff         max|err|=0.202876
```

`L1 step`, `all-pairs Euclidean` and `CDF meandiff` are unchanged by the
z-score fix to float precision (translation-invariant structurally, so the
mean-centering step of z-scoring cannot move them; only `radius-from-origin`
moved, from 0.200161 to 0.199525, because a distance "from the origin" is
NOT translation-invariant and the origin shifts when the series is
centered). Translation invariance is only half the argument — it does not
cover the σ-division half of z-scoring. `L1 step` and `all-pairs Euclidean`
survive that half because §A3 evaluates them through `expfit_meandiff`'s
default `abs_prop` metric, which §3's per-bin derivation already proves
scale-invariant (histogram bin membership is unchanged when `d` and the
edges are rescaled by the same constant); `CDF meandiff` survives it
because it compares `lambda*d`, and `lambda = 1/mean(d)` scales by the
inverse of whatever `d` scales by, so the product is scale-free on its own
terms. `radius-from-origin` reads each embedded point's own distance
from the origin instead of the distance between consecutive points. `L1
step` swaps the Euclidean distance for a taxicab one. `all-pairs Euclidean`
reads the distance between every pair of embedded points, not only
temporally consecutive ones. `CDF meandiff` drops the histogram entirely
and compares the empirical and fitted CDFs pointwise (no bin count to
guess). None of the four improves on §3's own best reading.

## 5. Why this stops here rather than continuing to guess

`CLAUDE.md`'s own words: "The dominant historical defect is a claim written
before it was measured." Shipping any of the 34 distinct structural
readings measured above (30 histogram variants + 4 alternative
distance/comparison readings, one of them — bins=5 / zero-to-max /
proportions — measured on both the 8-frame and 25-frame sets in §A1/§A2 —
plus the 21-point fine bin sweep of the closest fixed reading, plus the 3
data-driven bin-count rules and numpy's `auto` tie-break in §A2b) as
`C22EMBEDDINGDIST_100` would be exactly that claim — a correctness story
with no confirming measurement on every frame, on a feature whose only full
specification is the GPL-3.0 reference's source, which the issue explicitly
forbids reading or porting from. Using that reference as a black-box oracle
(never reading it, only calling it) is this fork's own established
practice for settling ambiguous catch22 details (`c22_ami2`,
`c22_acf_first_min`), and it was applied here in good faith across the
structural choices the public definition leaves open — delay rule,
embedding distance, histogram convention (both fixed AND data-driven bin
counts), comparison metric — getting to 30 of 33 frames matching to float
precision under the closest reading (§A2b), but not finding one that
reproduces the oracle on every frame tried.

**Outcome: measured revert.** No `pandas_ta/statistics/c22_embedding_dist.py`,
no `tests/test_c22_embedding_dist.py`, no `Category`/`core.py`/README/
`IndicatorDictionary.md` entry exists in this branch. This file and
`docs/measure_c22_embedding_dist.py` are the receipt. Per the issue: "A
measured revert closes this exactly as well as a ship."

## 6. Gate F — suites

No module was added, so there is nothing module-specific to run. The
required subset (unaffected by this attempt, since no shipped file
changed) and the whole suites are the launcher's to confirm in clean
worktrees.
