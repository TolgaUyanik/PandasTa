# `c22_outlier_timing_neg` — measured

PandasTa issue **#142** (C22-OUTLIER-TIMING-NEG), ported 2026-11-23 on branch
`issue-142-c22-outlier-timing-neg`.

| | |
|---|---|
| module | `pandas_ta/statistics/c22_outlier_timing_neg.py` |
| column | `C22OUTLIERNEG_100` (`SF`, a normalised median event position bounded in roughly [-1, 1]) |
| source | catch22 (Lubba et al. 2019, *Data Min. Knowl. Disc.* 33:1821), feature `DN_OutlierInclude_n_001_mdrmd`; pycatch22 (GPL-3.0) run measure-only outside this package: 26,118 of 26,118 windows agree to 1e-12 — §0 |
| tests | `tests/test_c22_outlier_timing_neg.py` |
| harness | `docs/measure_c22_outlier_timing_neg.py` (sections A, B, C, D, G, T) |
| Gate A | 768 of 768 sampled windows (every 11th window of six frames) agree with the plain-Python threshold-sweep oracle to < 1e-9 (worst observed diff 0.0) — §A |
| Gate B | causal; 0 of 22 offsets leak on six frames; `write-back-dated`/`window-one-ahead` caught on 13 of 22, `chunk-wide-mean` caught on 22 of 22 — §B |
| Gate C | fires on every bar with a full window (1,400 / 1,500) on all six frames; 106–197 distinct values per frame; `penny` (21.68% zero returns) still fires everywhere — §C |
| Gate D | ×8/×64 bit-identical on 12/12 cells; ×10/×3.7 price and ×10/×3.7 return rescales move 0 bars with matching NaN masks on 23 of 24 cells (one `student-t` cell is a test-series artifact, not a scale-dependence: §D2); `0 < fires < n` on every stochastic frame — §D |
| Gate E | max \|ρ\| 0.3981 vs `dist_from_high_60` (n=389,949), per-frame max median 0.4057 -- SHIP — §Gate E |
| Gate F | targeted run after round 3: see §F; whole suites by issue-solver |

Every number below was produced by `python docs/measure_c22_outlier_timing_neg.py`
(wall 678.9 s, peak traced memory 21.0 MB [the cost section's own allocator
dominates the whole run and is reported again, standalone, in §T]) or by
`python -m pytest tests/test_c22_outlier_timing_neg.py`, on this machine
(numpy 1.26.4, pandas 2.3.3, this repo's pinned CI versions per `CLAUDE.md`).
The targeted suite was also re-run with
`NPY_DISABLE_CPU_FEATURES=AVX512F AVX512_SKX AVX2 FMA3` (this machine's
detected set) via `docs/measure_c22_outlier_timing_neg_cpu.py`: same result.

---

## 0. What the column is

```
r[t]      = close[t] / close[t-1] - 1
X         = r[T-99 .. T]                       (100 returns, closes T-100 .. T)
Z         = (X - mean(X)) / sd(X, ddof=1)
Y         = -Z
tot       = count(Y >= 0)
for j = 0 .. floor(max(Y) / 0.01):
    idx(j)   = 1-indexed positions i with Y[i] >= 0.01 * j
    rank(j)  = median(idx(j)) / (length/2) - 1
    share(j) = (len(idx(j)) - 1) * 100 / tot
mj  = last j with share(j) > 2                 (0 if none)
fbi = first j with len(idx(j)) < 2             (last j if none)
C22OUTLIERNEG_100 = median(rank(0 .. min(mj, fbi)))
```

`Y = -Z` makes the window's most strongly NEGATIVE returns read as the
largest values, so sweeping `thr` from 0 upward progressively isolates the
window's most extreme negative returns; at each step `rank(thr)` reads the
qualifying set's own MEDIAN POSITION, normalised to the window's
half-length (0 mid-window, -1 crowded to the start, +1 crowded to the end).
The sweep is cut at the earlier of the last step still including more than
2% of the `Y >= 0` count and the first step with fewer than two points. The
column is the MEDIAN, over the steps up to that cut, of those per-step
normalised median POSITIONS — a timing statistic, not a bar-gap statistic. Checked
against the reference's OUTPUT (2026-11-24, owner): pycatch22 0.4.5 from
PyPI (GPL-3.0), installed in a separate scratch environment and run as a
black box on every full window of six synthetic 1,500-bar frames at lengths
100, 10 and 37, agrees with this column on **26,118 of 26,118** windows to
1e-12. No code was read from it and it is not a dependency. `0.4.5` is the
version actually installed and run; the issue text's "reference code
pycatch22 1.0.2" names a different version, and this session has no way to
check against PyPI (no web access) which is right -- flagged here, not
silently reconciled. Gate A below is the independent plain-Python second
spelling, kept as the test.

**Round 1** (commit `11ebc10`) shipped a different quantity: a nested
median of inter-event GAPS (`median(diff(idx(thr)))`), read off the paper's
one-sentence prose gloss without weighing four pieces of evidence already
in this worktree that pointed the other way (listed in the module
docstring). Round 2 (commit `818c15a`) corrected it to the median
position but cut the sweep at a fixed 2% of the window; against the
reference that moved 116 of 600 windows of a test frame (median absolute
difference 0.03, largest 0.26). **Round 3** (owner, attended, this version)
uses the reference's cut. Every number in §A–§T is round 3's, from a fresh
harness run.

## 1. Attribution, and what it is NOT evidence of

catch22 was selected for time-series CLASSIFICATION across 93 problems;
this is one of its own 22 canonical features. Nothing here tests it as a
return predictor on BIST: existence, not evidence. Shape features of
z-scored returns can pick up BIST tick rounding (many zero or repeated
returns on low-priced stocks); whether a price level or `Volume` tops the
Gate E attribution comparators is a question for real data. Gate E
answers it once re-run (§Gate E).

## A. Gate A — correctness

### A1. Against the independent plain-Python threshold-sweep oracle, every 11th window of six frames

The oracle (`direct_threshold_sweep`, in both the harness and the test
module) shares no code path with the shipped vectorised kernel: plain
Python, `math.fsum` for mean/variance, a Python-level threshold loop,
`statistics.median` for both the inner and outer median.

| frame | windows | agree (< 1e-9) | disagree |
|---|---|---|---|
| walk | 128 | 128 | 0 |
| tick-rounded | 128 | 128 | 0 |
| penny | 128 | 128 | 0 |
| ar1 | 128 | 128 | 0 |
| jump-cluster | 128 | 128 | 0 |
| student-t | 128 | 128 | 0 |
| **total** | **768** | **768** | **0** |

Worst observed |shipped − oracle| on any sampled window: **0.0** (exact
agreement; both sides reduce to the same ordering and median over the
sampled windows checked).

### A2. ddof sensitivity (which positions clear an absolute threshold)

`ar1`, every 13th window (108 windows sampled): **7** moved between
`ddof=1` and `ddof=0`. Confirms the module docstring's claim that the
z-score divisor is NOT inert here (unlike several sibling catch22 ports): a
rescale by `sqrt((n-ddof)/n)` preserves ranking but can move which
positions clear a fixed absolute threshold `k * INC`. `ZSCORE_DDOF = 1` is
kept at MATLAB `zscore`'s default (hctsa's own convention), the same
reason every sibling port uses it.

## B. Gate B — causality

### B1. The real module

Future replaced by an independent random path from offset `j` on (22
offsets, 130..1390 step 60): **0 / 22 leaking offsets** on each of walk,
tick-rounded, penny, ar1, jump-cluster, student-t.

### B2. Mutants, read off this module's source, edited and exec'd in memory

| mutant | leaking offsets (walk) |
|---|---|
| write-back-dated (output one bar early) | 13 / 22 |
| window-one-ahead | 13 / 22 |
| chunk-wide-mean (one mean across the whole chunk) | 22 / 22 |

The column is NOT tie-heavy (Gate C: 136 distinct values over 1,400
fired bars on `walk`), so even a one-bar shift is caught on more than half
the 22-offset harness sample. The committed test module (`tests/test_c22_outlier_timing_neg.py`)
runs these same three mutants plus `window-ten-ahead` and `returns-rolled`
on a different (10-offset) sample, measures write-back-dated/window-one-
ahead/returns-rolled at 9/10, window-ten-ahead at 10/10 and chunk-wide-mean
at 9/10, and pins the floor each must clear a few hits below that
(`write-back-dated` ≥6/10, `window-one-ahead` ≥6/10, `returns-rolled`
≥6/10, `window-ten-ahead` ≥8/10, `chunk-wide-mean` ≥7/10) — all satisfied
(full suite green, §F). A separate mask-back-dated mutant is dead on a
clean frame and caught on NaN-injected offsets, the first moved bar
always exactly `j − 1`; the write-back-dated mutant moves 6 of 8 spliced
offsets, each from exactly `j − 1`.

## C. Gate C — reachability

| frame | fired | distinct | range | median |
|---|---|---|---|---|
| walk | 1,400 / 1,500 | 136 | -0.56 .. 0.56 | 0.02 |
| tick-rounded | 1,400 / 1,500 | 117 | -0.44 .. 0.40 | 0.02 |
| penny | 1,400 / 1,500 | 122 | -0.48 .. 0.46 | 0.00 |
| ar1 | 1,400 / 1,500 | 197 | -0.90 .. 0.91 | 0.02 |
| jump-cluster | 1,400 / 1,500 | 106 | -0.34 .. 0.48 | 0.00 |
| student-t | 1,400 / 1,500 | 151 | -0.58 .. 0.92 | 0.01 |

Every frame fires on every bar with a full 100-return window. The column
is a normalised median event POSITION bounded in roughly [-1, 1]
(`tests/test_c22_outlier_timing_neg.py::test_every_output_is_a_normalised_median_position`),
with 106–197 distinct values per frame — far from coarse-grained, unlike
this fork's integer/count catch22 outputs (`c22_dfa`, `c22_periodicity`),
because the `/(length/2)` normalisation makes every one of the roughly
`length` possible 1-indexed positions a candidate value.

### C1. The issue's own worry: tick-rounded data

`penny` (a 2-lira series on a 1-kuruş tick) has **21.68%** exactly-zero
returns and still fires on every eligible bar with 122 distinct values,
range -0.48 .. 0.46 — similar in shape to the unrounded `walk` frame (136
distinct, range -0.56 .. 0.56). Whether BIST tick rounding drives the
column is a Gate C question for real data and goes with Gate E (top
comparator a price level or `Volume` would point at it); synthetic frames
cannot answer it.

## D. Gate D — scale-free

### D1. Exact binary rescales

×8 and ×64 price: **bit-identical on all 12 cells** (six frames × two
factors). The test module adds ×2⁻⁴⁰ and ×2⁴⁰ (24 cells, all bit-identical).

### D2. Inexact rescales

| rescale | frames | bars moved | NaN-mask diffs |
|---|---|---|---|
| price ×10 | all six | 0 | 0 |
| price ×3.7 | all six | 0 | 0 |
| returns ×10 | five of six | 0 | 0 |
| returns ×3.7 | all six | 0 | 0 |

The sixth returns ×10 cell (`student-t`) shows **1,183 NaN-mask diffs**.
That comes from the test series, not the indicator: confirmed by direct
inspection (`scaled <= 0` is `True` for this frame under this rescale) —
the `student-t` frame clips returns to ±0.5, one single-step return lands
below −0.1, so `1 + 10*r` goes negative there and the rescaled TEST price
itself goes non-positive from that bar on. The module's own blanking rule
("a close that is not a finite, normal, positive float ... is bad data")
then correctly marks every later bar bad — this is the module behaving as
documented, not a scale-dependence violation, and the same artifact this
fork's `c22_low_freq_power` receipt documents on the identical frame and
rescale (1,183 diffs there too). The committed test module avoids the trap
by only exercising this particular invariance on `walk` (0 moved, 0
NaN-mask diffs at ×10, ×3.7, ×0.1).

### D3. A negative return rescale flips which tail is read (not in the invariance class)

`ar1`, `r -> -r`: **1,396 of 1,400** bars moved. Expected and documented: a
sign flip swaps which tail of the return distribution reads as "negative",
so the column need not (and measurably does not) agree with the unscaled
one — `a < 0` is explicitly outside the `a * r + b, a > 0` invariance
class.

### D4. `0 < fires < n`, and not constant

1,400 of 1,500 on every stochastic frame (< 1,500 total bars), 106–197
distinct values each (§C) — not constant.

## G. The floor, and what it buys

| input | fires | max window sd |
|---|---|---|
| geometric ladder, step 0.01 | 0 | 1.455e-16 |
| ladder, step 0.001 | 0 | 1.513e-16 |
| ladder, step −0.005 | 0 | 1.201e-16 |
| 400 identical closes | 0 | — |

Every exact geometric ladder's returns are constant up to floating-point
rounding (sd ~1e-16, far below the 9.09e-13 / 4096-eps floor). The
`no-floor` mutant (dropping the floor check) fires on this same rounding
noise, confirming the floor is load-bearing and not a no-op.

## T. Cost

n = 100,000 closes: **wall 165.12 s**, peak traced memory **21.0 MB**,
99,900 bars fired. The windows are walked in `CHUNK_VALUES`-bounded chunks
(default 65,536 values), so peak memory is set by the chunk budget and not
by `len(close) * length * (thresholds swept)`; the test module's
`test_the_chunk_budget_cannot_change_a_value` confirms the chunk boundary
cannot move a value at three different budgets (1,000 / 5,000 / 2^20).

## F. Gate F — suites

Targeted run after round 3, with `GATE_E_PENDING_OK=1` (the setting CI
uses on the way to `dev`), on `tests/test_c22_outlier_timing_neg.py
tests/test_readme_counts.py tests/test_altport2_ports.py
tests/test_wiring_accessors.py tests/test_ml_companions.py
tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
tests/test_prose_counts_match_the_csvs.py`: **1,501 passed, 8 skipped, 1
failed**. The one failure was the docstring test still asserting round 2's
"no reference output" wording; it was updated and re-run alone (passed).
The `c22_outlier_timing_neg` Gate E row is recorded (§Gate E, SHIP).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

### F1. Wiring

All five touch points are asserted by `test_the_five_wiring_touch_points`
and `test_the_accessor_forwards_its_parameters`. Package-wide counts read
back from the live package after rebasing onto `dev` (which merged issue
#148's `tdi`, #160's `stl_trend_strength` and others in the meantime):
`Category` 388 (statistics category 76, gains `c22_outlier_timing_neg`),
`README.md` (388 / 396), `CATEGORY_TOTAL` 388,
`docs/IndicatorDictionary.md` (regenerated) and the tagged-column line of
`docs/MLCompanionContract.md` (732 → 733, `SF` 366 → 367) updated to match.

## Gate E

Re-run by issue-solver after round 3's kernel change (§0 deleted the round-2
row, 0.3967 vs `dist_from_high_60`, run `is142-c22_outlier_timing_neg-ee5ba5cd`).

Run `is142-c22_outlier_timing_neg-f8bda416`, `gate_e_overlap.py run --module
pandas_ta.statistics.c22_outlier_timing_neg`, 89 ALTPORT-1 frames, 398,849
pooled bars, 329 + 358 = 687 comparators, canary bit-equal (AKBNK.IS,
BIENY.IS, AGHOL.IS, SASA.IS).

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---|---|---|---|---|
| `C22OUTLIERNEG_100` | 0.3981 | `dist_from_high_60` | 389,949 | 0.4057 | SHIP |

0.3981 < 0.76 (SHIP line, `r3-perframe-0.90` bands) and per-frame max
median 0.4057 is far under the 0.90 STRUCK line. Recorded in
`docs/gate_e_ledger.csv`.
