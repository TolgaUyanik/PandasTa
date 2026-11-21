# `c22_embedding_dist` — measured and reverted

PandasTa issue **#132** (C22-EMBEDDING-DIST), attempted 2026-11-21 on branch
`issue-132-c22-embedding-dist`. **No `pandas_ta` module, test or wiring entry
was added.** Gate A could not be cleared honestly, so nothing ships; this
file is the receipt.

| | |
|---|---|
| candidate | catch22 (Lubba et al. 2019, *Data Min. Knowl. Disc.* 33:1821), feature `CO_Embed2_Dist_tau_d_expfit_meandiff` — the hctsa operation `CO_Embed2_Dist(y,'tau')`, exponential-fit misfit of consecutive distances in a 2-D delay embedding — proposed on the last 100 daily simple returns |
| harness | `docs/measure_c22_embedding_dist.py` (sections A0-A3; opt-in use of `pycatch22` 1.0.2 as a BLACK-BOX ORACLE ONLY, never read as source, never imported outside this one `docs/` script) |
| Gate A | **UNRESOLVED.** 25-frame broad sweep: max \|err\| 1.245120 against the best-effort candidate (§A1). Isolating the delay parameter (8 frames built so `tau = 1` under every plausible convention, §A2): best of 30 histogram variants max \|err\| 0.028614 (bins=10, min-to-max edges, density comparison); a further 21-point fine bin sweep of that same reading plateaus at max \|err\| 0.020-0.054, not converging toward 0. Four more structural readings (§A3) all stayed at max \|err\| ≥ 0.20. No reading tried reproduces the oracle. |
| Gate B/C/D | not attempted — no module exists to test |
| Gate E/F | not applicable — nothing shipped |
| outcome | **measured revert** per issue #132: "a measured revert closes this exactly as well as a ship" |

Every number below is `python docs/measure_c22_embedding_dist.py`'s own output
on this machine (numpy 1.26.4, pandas 2.3.3, Python 3.11, `pycatch22` 1.0.2
present in this worktree).

---

## 0. What was tried, and why it stopped here

The issue's own instruction is narrow: "port from the paper's and hctsa's
definitions, never from that code" (the reference, `pycatch22` 1.0.2, is
GPL-3.0; this fork is MIT). The paper and hctsa's published operation
description settle the SHAPE of the feature and nothing more:

1. z-score the series (inert here, like every other catch22 port in this
   fork — see §1);
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
calling it and comparing outputs, the same thing §A0-A3 below do. For this
feature that process did not converge.

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

The single most literal reading of the six-step paragraph above — `tau`
from `CO_FirstZero('ac')` capped near `N/10`, 5 bins spanning `[0, max(d)]`,
mean absolute difference of bin PROPORTIONS — checked against the oracle on
25 synthetic frames (iid normal, a random walk, a noisy 17-bar sine, an
AR(1) at phi 0.7, and a Student-t(3) path, five each, lengths 60-300):

```
A1. Broad sweep, 25 mixed frames, candidate(bins=5, zero_to_max, abs_prop):
    n=25  max|err|=1.245120  mean|err|=0.308518
    oracle's own range on these 25 frames: 0.029989 .. 1.358727
```

A max error of 1.245120 against an oracle range of 0.029989 to 1.358727
means the candidate is not a loose approximation, it is reading a
different quantity.

## 3. §A2 — isolating the delay parameter

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

30 histogram variants (bins in `{3, 5, 10, 20, 40}` x edges `{zero-to-max,
min-to-max}` x metric `{proportion, count, density}`), `tau` fixed at 1,
against the same 8 frames' oracle values:

```
    bins  edges        metric       max|err|
       3  zero_to_max  abs_prop     0.094732
       3  zero_to_max  abs_count    27.722673
       3  zero_to_max  abs_density  0.154823
       3  min_to_max   abs_prop     0.171363
       3  min_to_max   abs_count    22.834991
       3  min_to_max   abs_density  0.049317
       5  zero_to_max  abs_prop     0.203956
       5  zero_to_max  abs_count    18.384777
       5  zero_to_max  abs_density  0.126406
       5  min_to_max   abs_prop     0.271793
       5  min_to_max   abs_count    13.071413
       5  min_to_max   abs_density  0.049516
      10  zero_to_max  abs_prop     0.298427
      10  zero_to_max  abs_count    9.491685
      10  zero_to_max  abs_density  0.095887
      10  min_to_max   abs_prop     0.347047
      10  min_to_max   abs_count    6.553204
      10  min_to_max   abs_density  0.028614
      20  zero_to_max  abs_prop     0.360344
      20  zero_to_max  abs_count    4.717885
      20  zero_to_max  abs_density  0.086337
      20  min_to_max   abs_prop     0.382255
      20  min_to_max   abs_count    3.241805
      20  min_to_max   abs_density  0.046496
      40  zero_to_max  abs_prop     0.390094
      40  zero_to_max  abs_count    2.270201
      40  zero_to_max  abs_density  0.073727
      40  min_to_max   abs_prop     0.400591
      40  min_to_max   abs_count    1.473728
      40  min_to_max   abs_density  0.085701
    best: bins=10 edges=min_to_max metric=abs_density max|err|=0.028614
```

The `abs_count` metric reads far worse than either `abs_prop` or
`abs_density` here (6.5 to 27.7 against an oracle range of 0.297 to
0.422 on these 8 frames, not a close call); its apparent scale mismatch
is a property of these particular 8 frames' similar pair counts, not a
structural disqualifier (§1 above withdraws the earlier, wrong, "ruled
out analytically" claim for `abs_density`, and `abs_count` is simply the
worst performer measured rather than excluded on theory).

The density reading is the closest found by a wide margin, so its bin
count was swept finely (4 to 24, `min_to_max` edges) to check whether
the 10-bin result above was a lucky stopping point that would reach ~0
nearby:

```
    bins 4..24: max|err| ranges 0.020069 .. 0.054088 (best at bins=8)
    bins 4..24: mean|err| ranges 0.010722 .. 0.024549
```

It plateaus at a max error of 2-5% rather than converging toward zero —
close enough that a casual reader might call it "basically right," but
a genuine match should round to the oracle's own float precision (as
`c22_acf_first_min`'s §P reports 0 of 8,400 windows disagreeing against
the same kind of oracle), not sit at a 2-5% floor across 21 different
bin counts. This is a real, persistent residual, not a rounding gap or
an unlucky parameter choice.

## 4. §A3 — alternative structural readings

Four more readings of "distance in the embedding", same 8 tau-pinned
frames:

```
A3. Alternative structures, tau=1, bins=5 / zero_to_max / abs_prop where applicable:
    radius-from-origin   max|err|=0.200161
    L1 step              max|err|=0.203670
    all-pairs Euclidean  max|err|=0.323581
    CDF meandiff         max|err|=0.202876
```

`radius-from-origin` reads each embedded point's own distance from the
origin instead of the distance between consecutive points. `L1 step`
swaps the Euclidean distance for a taxicab one. `all-pairs Euclidean`
reads the distance between every pair of embedded points, not only
temporally consecutive ones. `CDF meandiff` drops the histogram
entirely and compares the empirical and fitted CDFs pointwise (no bin
count to guess). None of the four improves on §3's own best reading.

## 5. Why this stops here rather than continuing to guess

`CLAUDE.md`'s own words: "the dominant historical defect is a claim written
before it was measured." Shipping any of the 35 structural variants tried
above (1 broad-sweep reading, 30 histogram variants, 4 alternative
distance/comparison readings — plus the 21-point fine bin sweep of the
closest of those 30) as `C22EMBEDDINGDIST_100` would be exactly that
claim — a correctness story
with no confirming measurement, on a feature whose only full specification
is the GPL-3.0 reference's source, which the issue explicitly forbids
reading or porting from. Using that reference as a black-box oracle (never
reading it, only calling it) is this fork's own established practice for
settling ambiguous catch22 details (`c22_ami2`, `c22_acf_first_min`), and
it was applied here in good faith across the structural choices the public
definition leaves open — delay rule, embedding distance, histogram
convention, comparison metric — without finding one that reproduces the
oracle.

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
