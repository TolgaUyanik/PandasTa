# TS-REOCCUR-20 — `ts_reoccur_20`, measured

PandasTa issue **#103** (parent #31 ALPHASETS, screen of 2026-10-24).
Module `pandas_ta/statistics/ts_reoccur_20.py`, column **`TS_REOCCUR_20`**.
Tests `tests/test_ts_reoccur_20.py` (223).

Every number in §A1–§A6, §B, §C, §D, §G, §O, §L and §W, and §Z's traced
peak,
is printed by `python docs/measure_ts_reoccur_20.py` on this worktree
(**pandas 2.3.3, numpy 1.26.4** — which that script prints as its first
line, so this parenthesis is a quote and not a guess), section by section.
The headings take their letters from the script, with one join: the
script's section **M** (the mutants) is printed here under §B, because it
is Gate B's evidence. §E and §F are headings of this file and not of the
script.

Two frame sets are used throughout and the counts depend on which:

* the **seven grid frames** (`grid-2tick`, `grid-10tick`, `grid-40tick`,
  `grid-200tick`, `range-bound`, `round-1000`, `heavy-tailed`) — the
  script's `NAMES`, the test module's `VARYING`;
* those **plus `continuous`**, eight in all — the script's `ALL_NAMES`,
  the test module's `FRAMES`. The continuous frame is in Gate A, B and D
  because the column is a constant 0.0 there and bit-equality still means
  something; it is out of every claim about variation.

Each frame is 1,500 bars and fires on **1,481** of them (`length` CLOSES,
so the warm-up is `length - 1 = 19`), which makes the pooled figure
**11,848** over eight frames and 10,367 over seven.

What does NOT come from that command, marked again where it appears:

* **§Z's milliseconds**, which it does print but which are not a claim:
  they are this machine's and this run's. §Z gives three whole runs of a
  best-of-3 and states what survives a re-run — the flat traced peak, the
  monotone ordering and the ratio;
* **§E**, which is **OWED**: Gate E is run by issue-solver after this
  session;
* **§E0**, the 2026-10-24 screen's figures, measured on the PROTOTYPE and
  quoted from issue #103;
* **§F**, which is pytest's own output;
* **§C1's dictionary and contract deltas** (343 → 344 probed, 341 → 342
  registered, 349 → 350 callable, statistics 49 → 50, 686 → 687 tagged,
  42 → 43 `CONST`), which are read off
  `git diff docs/IndicatorDictionary.md` and re-derived against the live
  package by
  `tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.

```
x            = close[T - length + 1 .. T]
TS_REOCCUR   = #{ i : x[i] == x[j] for some j != i } / length
```

**Source.** tsfresh `feature_calculators.
percentage_of_reoccurring_datapoints_to_all_datapoints` (MIT), as issue
#103 applies it: "on 20 closes". The quantity the name states is "# of
data points occurring more than once / # of all data points", i.e.
`value_counts()[value_counts() > 1].sum() / len(x)` — the share of the
window's **bars** whose close has a twin, not the share of its distinct
**values** that are repeated. That second reading is tsfresh's SIBLING
function `percentage_of_reoccurring_values_to_all_values`, and §A4 prices
it as a different column.

The screen prototype is `docs/issues/screen/ind_screen.py` candidate
`ts_reoccur_20`, `roll(c, 20, w_pct_reoccurring)`, whose helper is

```python
def w_pct_reoccurring(W):
    S = np.sort(W, 1)
    eq = S[:, 1:] == S[:, :-1]
    dup = np.zeros_like(S, dtype=bool)
    dup[:, 1:] |= eq; dup[:, :-1] |= eq
    return dup.mean(1)
```

⚠ **tsfresh is not installed in this worktree and web access is
unavailable.** It is an ATTRIBUTION, not an oracle:
`tests/test_ts_reoccur_20.py::test_the_source_library_is_not_installed_here`
records that. What Gate A checks is the quantity the source's NAME states,
spelled two independent ways — a per-window `pandas.Series.value_counts()`
counter and the prototype's sort-and-compare — against the module, bit for
bit. The function name and the 20 are the issue's own. Nothing here is
evidence about what tsfresh does with an edge the issue does not name; the
one such edge that matters, a missing close, is §A4's last table, where
this fork's rule and the source's differ by construction.

---

## Verdict

| Gate | Result |
|---|---|
| A Correctness | **PASS, and it is bit-equality rather than a tolerance.** The module's only arithmetic is one integer count divided by `length`, so a per-window `value_counts()` oracle and the retyped screen prototype agree with it on **11,848 of 11,848** fired bars over eight frames with identical NaN masks, and at `length` 2, 3, 5, 21, 60 and 250. The output lattice is `k / length` with `k = 1` unreachable, measured absent at four lengths over all eight frames. |
| B Causality | **PASS.** 0 of 36 offsets leak on four frames and at `length` 2, 7, 60 and 250; the first fired bar is `length - 1` at every length. Six mutants: five live on every frame and each is the real column back-dated by a DERIVED number of bars, bit for bit (1,462 … 1,480 bars each). ⚠ The blind sweep catches those five at only 1 … 36 of 36 offsets, and §B says why — the column lives on a 21-point lattice. The sixth mutant shifts the bad-close mask's own index, is invisible to the sweep (0 of 36 on four clean frames) and is caught 12 of 12 on a designed frame, moving exactly bar J−1 at all twelve. |
| C Reachability | **PASS on synthetic data, OWED on real.** Fires 1,481 of 1,500 on each of eight frames, so `0 < fires < n` everywhere. 3 … 19 distinct values on the seven grid frames, spanning 0.00 … 1.00 across them. ⚠ On the `continuous` frame it is a CONSTANT 0.0 — 1 distinct value — which is the feature and not a failure (§A5). Gate C's real-data counts come from the Gate E run and are owed with it. |
| D Scale-free | **PASS.** ×8/×64 are EXACT and so cannot merge or split a tie: bit-identical on 11,848 of 11,848 bars over eight frames at both factors, at `length` 2 / 3 / 5 / 21 / 60 / 250, and at price levels 1e-6, 1e+6 and 1e+100. ×10 / ×3.7 / ×0.1 / ×1.0000001 are not exact and CAN merge two closes — bit-identical on all 11,848 at all four, and separately 0 merges in all 32 cells (bit-equality does not imply that; §D2) — and a frame of 20 consecutive doubles shows the merge happening, so that is a measurement and not a theorem. `price ** 2` and `price ** 0.5` keep every tie on all 10,367 grid bars. ⚠ The tick grid is not part of the column, so it is not comparable ACROSS instruments: §D4. |
| E Attribution | **Gate E: pending, run by issue-solver after this session.** |
| F Suites | This repo: 223 for the module, 223 again with `AVX512F AVX512_SKX AVX2 FMA3` disabled; the full-suite figure is in the commit message, and §F says why it is not here. The Backtesting suite is the launcher's. |

**What a consumer must know, in one place.** The column is a
**tick-grid** feature: it reads exact price equality, so it is identically
0.0 on continuous-float prices and its level is set by how many TICKS the
price moves in a bar (mean 0.9124 at one tick, 0.0379 at a hundred; §L1).
That makes it **negative volatility measured in ticks** — per-frame |ρ|
median 0.7974 against `stdev(close, 20)` within one tick regime (§O3),
against the screen's **0.7222** for the prototype on 89 real frames, where
`stdev` was the top of 687 comparators. It is **order-blind** (§A6) and
**not comparable across instruments** whose tick is a different fraction of
their price (§D4).

---

## E0 — what the screen measured, and on what

Quoted from issue #103; measured 2026-10-24 on the **prototype**, not on
this module.

| what | figure |
|---|---|
| Gate E max \|ρ\| | **0.7222** vs `stdev` (compute_all), n = 397,158 |
| top-5 per-frame max median | 0.7700 → **SHIP** |
| next comparators | `mad` 0.7099, `variance` 0.7090 |
| run | `screen_20261024`, 89 ALTPORT-1 frames, 398,849 bars, 329 + 358 comparators, canary bit-equal |
| fork overlap (stage 2, 12 frames, not Gate E) | max \|ρ\| 0.4851 vs `pvi:PVI_1`, per-frame max median 0.7451 |
| pre-flight (6 frames, `sanity.csv`) | prefix-causal, unchanged under price ×8 and volume ×8 |

Two things that line does and does not bound:

* the fork sweep's comparator set is every `Category` indicator at its
  defaults whose output, on the first frame, has **≥ 100 finite bars, an
  unchanged finite mask and a max relative difference under 1e-6 under
  price ×8, and a non-zero standard deviation**
  (`docs/issues/screen/fork_overlap.py:85-93`, read here, not re-run). So
  `LOT_ZERORET_60` — the nearest in-fork neighbour, §O2 — is in that pool
  **provided it cleared the non-constant test on that frame**, which
  `fork_overlap.csv` does not record and this worktree cannot check. With
  that caveat, 0.4851 is what bounds the prototype against it on those 12
  real frames;
* it says nothing about `ts_reoccur_20` against the **tsfresh variants of
  itself** that the screen's own `skipped.py:126` names as "variants of
  `ts_reoccur_20`" and never prototyped. There are **four**:
  `percentage_of_reoccurring_values`, `sum_of_reoccurring_values`,
  `sum_of_reoccurring_data_points` and
  `ratio_value_number_to_time_series_length`. §A4 prices **two** of them
  — the first and the last — and the nearest of those is
  rank-near-identical. The two `sum_of_…` variants are out of scope here
  for a reason that is not laziness: they sum PRICES rather than counting
  bars, so they carry the price level and are not scale-free, which makes
  them a different Gate D question and a different column.

---

## A1 — BIT-equality against the source's own quantity, and against the prototype

`python docs/measure_ts_reoccur_20.py A1`. Both oracles share no code with
the module: one is a per-window `pandas.Series.value_counts()`, the other
is the prototype's helper retyped from `ind_screen.py`.

| frame | fired | = oracle | = prototype | masks | max \|diff\| | mean |
|---|---|---|---|---|---|---|
| grid-2tick | 1481 | 1481 | 1481 | equal | 0.0e+00 | 0.7067 |
| grid-10tick | 1481 | 1481 | 1481 | equal | 0.0e+00 | 0.2254 |
| grid-40tick | 1481 | 1481 | 1481 | equal | 0.0e+00 | 0.0748 |
| grid-200tick | 1481 | 1481 | 1481 | equal | 0.0e+00 | 0.0094 |
| range-bound | 1481 | 1481 | 1481 | equal | 0.0e+00 | 0.5925 |
| round-1000 | 1481 | 1481 | 1481 | equal | 0.0e+00 | 0.6660 |
| heavy-tailed | 1481 | 1481 | 1481 | equal | 0.0e+00 | 0.2332 |
| continuous | 1481 | 1481 | 1481 | equal | 0.0e+00 | 0.0000 |
| **pooled** | **11,848** | **11,848** | **11,848** | | | |

**Why this is bit-equality and not luck.** The count is an integer and
`length` is an integer, so `count / length` is the correctly rounded value
of a rational — one rounding, in the same place, in all three spellings.
There is no summation order to differ about, which is the whole reason this
port's Gate A is cheaper than its siblings'. It is also why the module can
be bit-equal to the prototype *and* to a `value_counts()` counter at the
same time.

**Why the sort is the shipped spelling.** Sorting a window puts every run
of equal closes together, so a datapoint reoccurs exactly when it equals
its left or right neighbour in the sorted row — `value_counts()` without
building a counter per window. It is the prototype's own spelling, and
§Z's cost is the price of it: one sort per window, nothing carried between
them.

## A2 — the same at other lengths

`A2`, on `grid-2tick`.

| length | fired | = oracle | = prototype | masks | mean |
|---|---|---|---|---|---|
| 2 | 1499 | 1499 | 1499 | equal | 0.1534 |
| 3 | 1498 | 1498 | 1498 | equal | 0.2588 |
| 5 | 1496 | 1496 | 1496 | equal | 0.3889 |
| 21 | 1480 | 1480 | 1480 | equal | 0.7150 |
| 60 | 1441 | 1441 | 1441 | equal | 0.8655 |
| 250 | 1251 | 1251 | 1251 | equal | 0.9686 |

The mean rises with `length` because a longer window gives every close
more chances to find a twin — at 250 closes on a 0.01 grid almost every bar
has one.

## A3 — the lattice `k / length`, and why `k = 1` is unreachable

`A3`. A close with a twin contributes **at least two** bars to the count,
so `k = 1` cannot occur. Over all eight frames:

| length | `k` values reached | how many | `k = 1` present |
|---|---|---|---|
| 2 | 0, 2 | 2 | no |
| 3 | 0, 2, 3 | 3 | no |
| 20 | 0, 2, 3, …, 20 | **20** | no |
| 60 | 0, 2, 3, …, 60 | **60** | no |

(the count is `len(ks)`, printed by `section_A3`, not a count of the
ellipsis: at `length` 20 the lattice has 21 points, `k = 1` is the one
that cannot occur, and all 20 of the rest are reached across the eight
frames)

⚠ The lattice is exact as a **rational**, not as a round trip:
`count / length` is one correctly rounded double, and multiplying it back
by `length` rounds a second time — max `|k - round(k)|` is 0.0e+00 at
`length` 2, 3 and 20 and **3.6e-15** at `length` 60. The test recovers `k`
with a 1e-9 tolerance for that reason.

**The closed forms, all exact (max \|difference\| 0.0e+00):**

| frame | reading | bars, at `length` 2 / 3 / 20 / 60 |
|---|---|---|
| flat (300 × 100.0) | exactly **1.0** | 299 / 298 / 281 / 241 |
| one tick a bar (a ladder) | exactly **0.0** | 299 / 298 / 281 / 241 |
| two grid points only | exactly **1.0** on all 281 bars at `length` 20 | — |

⚠ The two-grid-point frame is **not** 1.0 at every length, and the reason
is worth stating because it is the only way the column reaches a value
just below 1: the only way a close there fails to have a twin is to appear
**exactly once** in the window, so the reachable set is
`{1.0, (length - 1) / length}` — and at `length` 2, where "appears once"
means the two closes differ, `{1.0, 0.0}`. Measured, as shares of the
fired bars:

| length | bars | the reading |
|---|---|---|
| 2 | 299 | 0.0000 on 0.4983, 1.0000 on 0.5017 |
| 3 | 298 | 0.6667 on 0.7282, 1.0000 on 0.2718 |
| 20 | 281 | 1.0000 on **all** |
| 60 | 241 | 1.0000 on **all** |

At `length` 20 a window of that frame's fair coin flips lands on one
side exactly once with probability 20 · 2⁻¹⁹ ≈ 3.8e-5 — arithmetic from
the frame's construction, not a measurement — so "1.0 on all 281" is
what to expect rather than a surprise. The test asserts the SET at every
length and the all-1.0 only at 20.

## A4 — the readings the issue's line leaves open, priced

`A4`. Each variant is computed over the same windows, with the same
missing-data rule, so the only difference is the statistic.

| frame | variant | masks | shared | bit-equal | max \|d\| | ρ | distinct |
|---|---|---|---|---|---|---|---|
| grid-2tick | `values_to_all_values` | equal | 1481 | 5 | 0.3667 | 0.9728 | 47 |
| grid-2tick | `distinct / length` | equal | 1481 | 81 | 0.7500 | −0.9318 | 14 |
| grid-2tick | `has_duplicate` (x > 0) | equal | 1481 | 5 | 0.8500 | — | **1** |
| grid-2tick | tolerance 1e-12 | equal | 1481 | **1481** | 0.0000 | 1.0000 | 18 |
| grid-2tick | tolerance 1e-4 | equal | 1481 | **1481** | 0.0000 | 1.0000 | 18 |
| grid-2tick | on 20 RETURNS | differ | 1480 | 0 | 0.9000 | 0.5954 | 14 |
| grid-10tick | `values_to_all_values` | equal | 1481 | 147 | 0.2423 | 0.9985 | 22 |
| grid-10tick | `distinct / length` | equal | 1481 | 2 | 1.0000 | −0.9868 | 9 |
| grid-10tick | `has_duplicate` | equal | 1481 | 147 | 0.9000 | 0.5248 | 2 |
| grid-10tick | tolerance 1e-12 / 1e-4 | equal | 1481 | 1481 | 0.0000 | 1.0000 | 13 |
| grid-10tick | on 20 RETURNS | differ | 1480 | 149 | 0.6500 | 0.3169 | 4 |
| grid-40tick | `values_to_all_values` | equal | 1481 | 644 | 0.1667 | 1.0000 | 7 |
| grid-40tick | `distinct / length` | equal | 1481 | 0 | 1.0000 | −0.9988 | 6 |
| grid-40tick | `has_duplicate` | equal | 1481 | 644 | 0.9000 | 0.9280 | 2 |
| grid-40tick | tolerance 1e-12 / 1e-4 | equal | 1481 | 1481 | 0.0000 | 1.0000 | 7 |
| grid-40tick | on 20 RETURNS | differ | 1480 | 644 | 0.5000 | 0.1637 | 2 |
| grid-200tick | `values_to_all_values` | equal | 1481 | 1346 | 0.0889 | 1.0000 | 3 |
| grid-200tick | `distinct / length` | equal | 1481 | 0 | 1.0000 | −1.0000 | 3 |
| grid-200tick | `has_duplicate` | equal | 1481 | 1346 | 0.9000 | 0.9999 | 2 |
| grid-200tick | tolerance 1e-12 | equal | 1481 | **1481** | 0.0000 | 1.0000 | 3 |
| grid-200tick | **tolerance 1e-4** | equal | 1481 | **1046** | **0.2000** | **0.4339** | 5 |
| grid-200tick | on 20 RETURNS | differ | 1480 | 1345 | 0.2000 | — | **1** |
| range-bound | `values_to_all_values` | equal | 1481 | 1 | 0.3273 | 0.9771 | 43 |
| range-bound | `distinct / length` | equal | 1481 | 106 | 0.7500 | −0.9550 | 11 |
| range-bound | `has_duplicate` | equal | 1481 | 1 | 0.8500 | — | **1** |
| range-bound | tolerance 1e-12 / 1e-4 | equal | 1481 | 1481 | 0.0000 | 1.0000 | 18 |
| range-bound | on 20 RETURNS | differ | 1480 | 0 | 0.8500 | 0.5408 | 9 |
| round-1000 | `values_to_all_values` | equal | 1481 | 3 | 0.3750 | 0.9726 | 47 |
| round-1000 | `distinct / length` | equal | 1481 | 112 | 0.6500 | −0.9268 | 12 |
| round-1000 | `has_duplicate` | equal | 1481 | 3 | 0.7500 | — | **1** |
| round-1000 | tolerance 1e-12 / 1e-4 | equal | 1481 | 1481 | 0.0000 | 1.0000 | 16 |
| round-1000 | on 20 RETURNS | differ | 1480 | 0 | 0.8500 | 0.3755 | 14 |
| heavy-tailed | `values_to_all_values` | equal | 1481 | 219 | 0.2444 | 0.9993 | 34 |
| heavy-tailed | `distinct / length` | equal | 1481 | 17 | 1.0000 | −0.9948 | 14 |
| heavy-tailed | `has_duplicate` | equal | 1481 | 219 | 0.9000 | 0.6225 | 2 |
| heavy-tailed | tolerance 1e-12 / 1e-4 | equal | 1481 | 1481 | 0.0000 | 1.0000 | 19 |
| heavy-tailed | on 20 RETURNS | differ | 1480 | 228 | 0.6500 | 0.6553 | 9 |

A dash in the ρ column is a Spearman of a CONSTANT, which is the finding
for `has_duplicate` rather than a gap: the boolean is constant on **3 of
the 7** grid frames — `grid-2tick`, `range-bound` and `round-1000`, which
are exactly the three that never read 0.00 in §C, so every window there
has a repeat somewhere. That count is printed by `section_A4` (which
counts the `distinct = 1` rows itself) rather than read off the table by
eye.

Five readings, decided:

1. **`datapoints_to_all_datapoints`, not `values_to_all_values`.** The
   issue names the first. They are different columns — 1 to 1,346 of 1,481
   bars equal, max \|difference\| up to 0.3750 — but **nearly
   rank-identical**, \|ρ\| 0.9726 … 1.0000, hitting 1.0000 on the two
   sparsest frames. So the choice barely moves a tree, and the docstring
   names which one this is rather than leaving a reader to assume.
2. **The window holds `length` CLOSES**, which is the issue's word. On
   `length` RETURNS it is a different column (\|ρ\| 0.1637 … 0.6553, and
   constant on `grid-200tick`) and fires one bar later, because `length`
   returns need `length + 1` closes.
3. **Equality is EXACT**, with no tolerance and no re-quantisation. A
   1e-12 relative tolerance changes nothing on any of the seven frames. A
   1e-4 one changes exactly `grid-200tick` — because 1e-4 of 100 **is one
   tick** there — and turns the column into a dispersion measure (ρ falls
   to 0.4339, max \|difference\| 0.2000). A tolerance is therefore not a
   robustness knob: it is a different feature whose scale is the grid's.
4. **It is the share, not the boolean.** `has_duplicate` is the same
   quantity thresholded at 0, and it is constant on 3 of 7 frames. The
   screen's `skipped.py` names the `has_duplicate` family as "booleans of
   `ts_reoccur_20`'s quantity"; this is that statement measured.
5. **`distinct / length` is not the complement.** 0 to 112 of 1,481 bars
   equal and max \|difference\| up to 1.0, but \|ρ\| 0.9268 … 1.0000 in
   the other direction — a near-mirror, not a mirror, because a value
   appearing three times removes two distinct slots and adds three
   reoccurring bars.

**The missing-data rule, which is this fork's and not the source's.** One
bad close at bar 200 of a 400-bar frame:

| close[200] | module fires | source-literal fires | bars only the literal fires on | what they read |
|---|---|---|---|---|
| `nan` | 361 | 381 | 20 | 0.50 … 0.80 |
| `inf` | 361 | 381 | 20 | 0.50 … 0.80 |
| `0.0` | 361 | 381 | 20 | 0.50 … 0.80 |
| `-100.0` | 361 | 381 | 20 | 0.50 … 0.80 |
| `5e-324` (subnormal) | 361 | 381 | 20 | 0.50 … 0.80 |

`value_counts()` drops a NaN from the numerator and `len(x)` keeps
counting it in the denominator, so the source-literal reading — which is
also the prototype's, since an unmatched NaN is never adjacent to an equal
value in a sorted row — reports a **deflated share** on the 20 windows
that hold the bad bar. A non-NaN bad close (0.0, −100.0, inf, a subnormal)
is worse in kind: the literal reading treats it as a perfectly good price
that happens to be unique. This fork empties those windows instead, which
is what every sibling in `statistics/` does.

## A5 — the continuous-float frame: identically zero, and that is the feature

`A5`. The disclosure that matters most for anyone reading the column on
non-BIST data.

| frame | fires | distinct values | max |
|---|---|---|---|
| continuous walk at price 1 | 1481 | **1** | 0.0000 |
| continuous walk at price 100 | 1481 | **1** | 0.0000 |
| continuous walk at price 1e+6 | 1481 | **1** | 0.0000 |

The raw walk has **0 duplicated closes of 1,500** — a float64 random walk
simply never revisits a price exactly. The SAME path on a 0.01 grid at
price 1 reads mean **0.7067**. So the column is not measuring the path; it
is measuring the path against the grid, and without a grid there is
nothing to measure. This is the `fvg` lesson of CLAUDE.md from the other
side: there, a tie-driven column was declared dead on continuous synthetic
frames and was alive on real prices (86,415 of 408,253 BIST daily bars
close exactly at an extreme); here the same arithmetic is what the issue
is asking for, and the synthetic frames have to carry the grid or they
measure nothing.

## A6 — order-blindness: the window's multiset is all it reads

`A6`.

* **2,000 of 2,000** random permutations of one 20-close window leave the
  value bit-identical (the window reads 0.9).
* A **reversed frame** gives the column reversed, bit for bit on **1,481
  of 1,481** bars, on each of the seven grid frames. A window of the
  reversed frame is a window of the original read backwards, and the
  column cannot tell the two apart.

So the column cannot see trend, sign, or where in the window a repeat sat
— only how many bars had a twin. That is a real limit (it is blind to
"the price has been pinned at the top of the range for five bars") and it
is also why it is cheap to reason about: no ordering, no weighting, no
centre.

---

## B — Gate B: the sweep, the six mutants, and why the sweep under-catches

`python docs/measure_ts_reoccur_20.py B M`.

**The real module leaks nothing.** Replacing every bar from offset `j`
onward with a second frame's values and comparing the prefix `[:j]`:

| frame | offsets that leak | of | first fired bar |
|---|---|---|---|
| grid-2tick | 0 | 36 | 19 |
| grid-10tick | 0 | 36 | 19 |
| grid-40tick | 0 | 36 | 19 |
| range-bound | 0 | 36 | 19 |

and at `length` 2 / 7 / 60 / 250 on `grid-2tick`: 0 leaks, first fired bar
1 / 6 / 59 / 249 = `length - 1` each time.

**The six mutants.** Each is the shipped module's own source, read off
disk, with one string replaced, compiled and `exec`'d in memory — so it is
this code with one index moved, not a re-implementation.

| mutant | the edit | caught by the sweep (of 36) | is the real column back-dated by |
|---|---|---|---|
| `back_date_two` | `Series(out, …).shift(-2)` | 27 / 14 / 4 / 31 | **2 bars**, 1479 of 1479 on each frame |
| `back_date_full` | `.shift(-(length - 1))` | 36 / 36 / 34 / 36 | **19 bars**, 1462 of 1462 |
| `write_index_earlier` | `out[length - 2:-1] = val` | 21 / 7 / 1 / 21 | **1 bar**, 1480 of 1480 |
| `forward_window` | `sliding_window_view(np.roll(c, -1), length)` | 21 / 7 / 1 / 21 | **1 bar**, 1480 of 1480 |
| `centred_window` | `np.roll(c, -(length // 2))` | 36 / 35 / 25 / 36 | **10 bars**, 1471 of 1471 |
| `shifted_bad_mask` | `np.roll(holds_bad, -1)` | **0 / 0 / 0 / 0** | see below |

(the four counts are `grid-2tick` / `grid-10tick` / `grid-40tick` /
`range-bound`; the back-dating is checked on every bar `np.roll`'s wrap
leaves alone, which is why the denominators differ by the shift)

**⚠ The blind sweep under-catches here, and that is a finding about the
column rather than about the mutants.** `TS_REOCCUR_20` lives on a
21-point lattice, so shifting it by a bar often lands on the same value
and the prefix comparison sees nothing. The catch rate tracks the frame's
**churn** — the share of adjacent fired bars where the column changes at
all:

| frame | churn | `back_date_two` caught | `write_index_earlier` caught |
|---|---|---|---|
| grid-2tick | 0.6466 | 27 | 21 |
| grid-10tick | 0.3236 | 14 | 7 |
| grid-40tick | 0.1128 | 4 | 1 |
| range-bound | 0.6155 | 31 | 21 |

This is exactly the failure mode CLAUDE.md's Gate B is written against —
"prefix truncation alone proves nothing" — reached from a new direction:
not back-dating that the sweep cannot see in principle, but a real
look-ahead that it misses 35 times out of 36 on a sparse frame. So the
assertion that carries Gate B here is the **derived displacement**: each
mutant IS the real column read `k` bars late, bit for bit, and `k` comes
from the edit rather than from a search. A mutant that the sweep catches
once and that equals `real(+1)` on 1,480 of 1,480 bars is proven to read
the future; a count of 1 of 36 on its own would not have.

**The sixth mutant, which the sweep cannot catch at all.** Shifting the
bad-close mask's own index makes bar T empty or not according to whether
the window ending at **T+1** holds a bad close. On a frame where no close
is bad the mask is all False, so the mutant is not even LIVE — it is
`equals()` to the real module on all four frames — and the sweep catches
it 0 of 36 times on each.

What it CAN move is derived, not searched: a bad close at J spoils the
windows ending at J … J+19, so the shifted mask empties the bars
J−1 … J+18, and **J−1 is the only one before J**. On a frame with a bad
close at each of 12 offsets ≥ `length` apart:

* the real module is caught at **0** of 12 (it empties only bars ≥ J);
* the mutant is caught at **12** of 12;
* the bars it moves before the offset are exactly `[J − 1]` at all twelve,
  under a moved-set definition that is mask flips **union** value changes
  (so a bar that keeps its mask and moves its double counts too).

---

## C — Gate C: reachability

`python docs/measure_ts_reoccur_20.py C`.

| frame | fires | of | distinct | min | max | mean | bars reading exactly 0.0 |
|---|---|---|---|---|---|---|---|
| grid-2tick | 1481 | 1500 | 18 | 0.15 | 1.00 | 0.7067 | 0 |
| grid-10tick | 1481 | 1500 | 13 | 0.00 | 0.65 | 0.2254 | 147 |
| grid-40tick | 1481 | 1500 | 7 | 0.00 | 0.50 | 0.0748 | 644 |
| grid-200tick | 1481 | 1500 | 3 | 0.00 | 0.20 | 0.0094 | 1346 |
| range-bound | 1481 | 1500 | 18 | 0.15 | 1.00 | 0.5925 | 0 |
| round-1000 | 1481 | 1500 | 16 | 0.25 | 1.00 | 0.6660 | 0 |
| heavy-tailed | 1481 | 1500 | 19 | 0.00 | 0.95 | 0.2332 | 219 |
| continuous | 1481 | 1500 | **1** | 0.00 | 0.00 | 0.0000 | 1481 |

`0 < fires < n` on all eight. The distinct counts are small **because the
lattice is small** — 20 reachable values at `length` 20 (§A3), of which a
single tick regime visits 3 to 19 — and they are pinned as a floor rather
than to the digit, because which grid point a generated close lands on
depends on `np.exp`'s last bits. The floor is **≥ 6** on six of the seven
grid frames and **≥ 2** on `grid-200tick`, whose third value (0.20) is
carried by **4** bars of 1,481 — the raw count `section_C` prints beside
each histogram share, because 0.003 cannot be read back as a count. A
floor of 3 there would sit exactly on the measurement.

The value histograms (share of fired bars, with the raw bar count in
brackets; the eight lowest lattice points 0.00 … 0.40. `section_C` prints
the eight lowest values PRESENT per frame, so readings above 0.40 —
`grid-2tick`, `range-bound` and `round-1000`'s 0.45 and up, and
`grid-40tick`'s 0.50 — are cut here and not there):

| frame | 0.00 | 0.10 | 0.15 | 0.20 | 0.25 | 0.30 | 0.35 | 0.40 |
|---|---|---|---|---|---|---|---|---|
| grid-2tick | — | — | 0.001 (1) | 0.003 (4) | 0.009 (14) | 0.009 (13) | 0.007 (10) | 0.024 (35) |
| grid-10tick | 0.099 (147) | 0.183 (271) | 0.027 (40) | 0.236 (350) | 0.082 (122) | 0.165 (244) | 0.062 (92) | 0.078 (115) |
| grid-40tick | 0.435 (644) | 0.393 (582) | 0.051 (75) | 0.095 (141) | — | 0.018 (27) | — | 0.007 (10) |
| grid-200tick | 0.909 (1346) | 0.088 (131) | — | **0.003 (4)** | — | — | — | — |
| range-bound | — | — | 0.001 (1) | 0.002 (3) | 0.006 (9) | 0.034 (51) | 0.024 (35) | 0.068 (101) |
| round-1000 | — | — | — | — | 0.001 (2) | 0.007 (10) | 0.013 (19) | 0.018 (27) |
| heavy-tailed | 0.148 (219) | 0.207 (306) | 0.021 (31) | 0.203 (300) | 0.049 (72) | 0.151 (223) | 0.030 (45) | 0.072 (106) |

(the first printed value for `grid-2tick` is 0.15 and for `round-1000`
0.25: those frames never read 0 at all, which is the same fact as their
zero column above)

### C1 — ⚠ the dictionary tags this column `CONST`, and that is the probe frame

`python docs/gen_indicator_dictionary.py` probes **one 600-bar
continuous-float synthetic frame**, where nothing repeats, so the
generated `docs/IndicatorDictionary.md` tags `TS_REOCCUR_20` as `CONST`
and lists it under *Never fires on the probe* — immediately below
`lot_zeroret_60`, which is in that table for exactly the same reason (a
zero return needs two equal closes). The generator is not editable from
this issue's file list and its output is a live probe, so the row stands
as generated.

⚠ That row's second cell reads "— unregistered, file one", and **that is
the generator's fallback for any indicator with no entry in its own
`DEAD_TASKS` table — `DEAD_TASKS.get(name, '— unregistered, file one')`
in `docs/gen_indicator_dictionary.py` — not a statement about
registration**: `ts_reoccur_20` is in
`Category["statistics"]` (`pandas_ta/__init__.py`) and on `df.ta`
(`pandas_ta/core.py`), pinned by
`tests/test_ts_reoccur_20.py::test_name_registration_and_accessor`. The
row above it, `lot_zeroret_60`, carries the same fallback for the same
reason.

What answers the CONST tag is the rule that table itself states —
*confirm on real data, then repair or delete*:

* the 2026-10-24 screen measured a **finite Spearman** for the prototype
  against 687 comparators over **n = 397,158** real BIST bars (§E0),
  which a constant column cannot produce;
* §A1 measures this module **bit-equal to that prototype** on every
  frame, so the real-data behaviour is the same column's;
* the pooled fired and non-zero counts from the 89 frames are **owed**
  with the Gate E run (§E), which is where that table's "confirm on real
  data" is actually discharged.

`docs/MLCompanionContract.md`'s tag counts carry the same warning, and
they move 686 → 687 tagged / 42 → 43 `CONST` rather than `SF`, because
the count is of what the dictionary observed and not of what the column
is. Those two deltas are read off `git diff docs/IndicatorDictionary.md`,
which adds exactly one **tagged output column** row
(`` `TS_REOCCUR_20` CONST ``) and one *Never fires on the probe* row, and
otherwise changes only the four package counts (343 → 344 probed,
341 → 342 registered, 349 → 350 callable, statistics 49 → 50).

⚠ **In the coarse regime the column is nearly a binary flag.**
`grid-200tick` reads 0.00 on 90.9% of bars and 0.10 on 8.8%, over 3
distinct values. That is the regime a BIST stock at 100 TRY on a 0.01 tick
sits in, and it is the honest shape of the feature there: "did any close
repeat in the last 20 bars". Gate E's real-data reachability counts will
say how much of the 89-frame universe looks like that; this file cannot.

---

## D — Gate D: scale-freedom

`python docs/measure_ts_reoccur_20.py D`.

### D1 — ×8 and ×64, which are exact

A scale by a power of two is exact (no overflow, no underflow), so
`8a == 8b` exactly when `a == b`: the rescale can neither merge nor split a
tie, and the output is bit-identical by construction.

| frame | fired | = ×8 | = ×64 | masks |
|---|---|---|---|---|
| each of the eight | 1481 | 1481 | 1481 | equal |
| **pooled** | **11,848** | **11,848** | **11,848** | |

and at other lengths on `grid-2tick` (bit-equal / fired): 2 → 1499/1499,
3 → 1498/1498, 5 → 1496/1496, 21 → 1480/1480, 60 → 1441/1441,
250 → 1251/1251; at price levels 1e-6, 1e+6 and 1e+100 (the frame moved
there first, then ×8): 1481/1481 at each.

### D2 — ×10, ×3.7, ×0.1, ×1.0000001, where a merge is possible

These are not exact. The direction of the risk is one-sided and provable:
equal doubles scale to the **same** double, so a rescale can never split a
tie; what it can do is **merge** two closes that differ in their last bits.
Measured over all eight frames and all four factors: bit-identical on
**1,481 of 1,481** bars in every cell, masks equal, and **0 merges**.

⚠ Those are two separate measurements and the second is not implied by
the first. A merge inside a window where both closes already had a twin
leaves the duplicate count — and so the column — untouched, and
`grid-200tick`, where 1,346 of 1,481 bars already read a repeat, is
exactly where that would hide. So `section_D` prints the merge count for
itself: `np.unique(close).size - np.unique(close * k).size` over the whole
frame, which is **m0** in all 32 cells (eight frames × four factors).

That 0 is a measurement about these frames, not a theorem — tick-grid
closes differ by ~1e-4 relative, twelve orders of magnitude more than a
double's spacing. §D3 builds the frame where the merge does happen.

### D3 — the forced merge

20 **consecutive doubles** (neighbours one ulp apart), which is the
adversarial input for an equality-based column:

| frame | ×1 | ×8 | ×64 | ×10 | ×3.7 | ×0.1 |
|---|---|---|---|---|---|---|
| from 1.9 | 20/20 distinct, **0.00** | 20/20, 0.00 | 20/20, 0.00 | **13/20, 0.70** | 18/20, 0.20 | 16/20, 0.40 |
| from 1.0 | 20/20, 0.00 | 20/20, 0.00 | 20/20, 0.00 | 20/20, 0.00 | 20/20, 0.00 | 20/20, 0.00 |

The split between the two rows is the ulp argument, measured: a ×10
product's ulp is 8 or 16 times the input's, and only in the larger binade
(mantissa ≥ 1.6, hence 1.9 and not 1.0) is `10·ulp` small enough for two
neighbours to round together. The powers of two never merge, at either
start.

### D4 — ⚠ the tick grid is NOT part of the column

The same return path quantised at two price levels on the same 0.01 grid:

| price | mean | fires | distinct |
|---|---|---|---|
| 5 | **0.2254** | 1481 | 13 |
| 500 | **0.0037** | 1481 | 2 |

Rescaling a **frame** rescales its grid with it, which is why §D1 passes
and why the column is scale-free in this fork's sense. Comparing two
**instruments** whose tick is a different fraction of their price does
not: a 5-TRY stock and a 500-TRY stock on the same 0.01 tick read this
column on different scales, and a tree pooling them cross-sectionally is
reading "is this a cheap stock" as much as "has it been quiet". BIST's own
tick size is a step function of price, which moves the effect but does not
remove it. This is the sharpest limit on the column and it is not
something Gate E measures: Gate E is a per-column correlation sweep, not a
cross-sectional comparability check.

### D5 — the power maps

`price ** 2` and `price ** 0.5` are not rescales, but they are **monotone**
and deterministic, so in exact arithmetic they preserve every tie and every
distinction; they round, so a merge is possible. Measured bit-identical,
masks equal, max \|difference\| 0.0000, on **1,481 of 1,481** bars of each
of the seven grid frames at both powers — 10,367 bars in total at each
power.

---

## G — the guards

`python docs/measure_ts_reoccur_20.py G`.

### G1 — a bad close empties its windows and nothing earlier

Six values × six positions, on a 400-bar frame. A bad close sits in
`length` windows and spoils exactly those, fewer near either end:

| bad close at bar | windows emptied | earlier bars moved |
|---|---|---|
| 0 | 1 | 0 |
| 1 | 2 | 0 |
| 18 | 19 | 0 |
| 200 | **20** | 0 |
| 398 | 2 | 0 |
| 399 | 1 | 0 |

identical for `nan`, `inf`, `-inf`, `0.0`, `-100.0` and `5e-324` — **36
(value, position) pairs, 0 earlier bars moved in any of them**. These
counts are window geometry rather than floating point, so they are pinned
to the digit.

### G2 — no float error is reachable

The module's only arithmetic is an integer division, so there is nothing to
overflow and nothing to divide by zero. All three of these run inside one
`np.errstate(all="raise")` block in `section_G`: an all-NaN frame fires
**0 of 400**, a frame of 400 zeros fires **0 of 400**, a frame of 400
negative prices fires **0 of 400** — and no error is raised. There is
no per-value bound here (its sibling `ts_energy_last_20` needs one because
it squares a return; this one compares) and no dispersion floor (its
siblings `ts_binent_20` and `ts_aggac_60` need one because they divide by a
spread; this one counts).

### G3 — the chunk budget is invisible

`CHUNK_VALUES` bounds the sorted copy and is not a parameter of the
statistic. Every chunk is an independent run of rows:

| `CHUNK_VALUES` | rows per chunk at `length` 20 | identical column |
|---|---|---|
| 1 | 1 | yes |
| 20 | 1 | yes |
| 999 | 49 | yes |
| 10**9 | 50,000,000 | yes |

### G4 — the degenerate frames are READINGS, not NaN

| frame | fires | range | distinct |
|---|---|---|---|
| flat (300 × 100.0) | 281 | 1.00 … 1.00 | 1 |
| one tick a bar | 281 | 0.00 … 0.00 | 1 |
| two grid points | 281 | 1.00 … 1.00 | 1 |

A window with no repeat reads exactly 0.0 and a window of 20 identical
closes reads exactly 1.0. Neither is missing data, and the source's own
`len(x) == 0` NaN is unreachable because `verify_series` refuses an input
shorter than `length`: 19 closes returns `None`, 20 closes fires on 1 bar.

---

## O — overlap

`python docs/measure_ts_reoccur_20.py O`. All of §O is **synthetic**. Gate
E, which is owed, is the measurement that decides the band.

### O1 — the full sweep, seven grid frames

n = 1,481 per frame. "pooled" is the signed Spearman over the
concatenation; the other four columns are \|ρ\| over the per-frame values,
which are listed in frame order.

| comparator | pooled | median | min | max | per frame |
|---|---|---|---|---|---|
| `LOT_ZERORET_20` | 0.7962 | 0.3480 | 0.1320 | 0.7286 | +0.318 +0.302 +0.449 +0.348 +0.371 +0.132 +0.729 |
| `LOT_ZERORET_60` | 0.8427 | 0.1907 | 0.0542 | 0.5027 | +0.267 +0.191 +0.262 +0.160 +0.183 +0.054 +0.503 |
| `NATR_20` | −0.2907 | 0.1704 | 0.0243 | 0.3653 | −0.224 −0.170 −0.111 +0.024 −0.288 −0.114 −0.365 |
| `stdev(returns, 20)` | −0.2892 | 0.1789 | 0.0428 | 0.3210 | −0.179 −0.120 −0.071 +0.043 −0.283 −0.227 −0.321 |
| `stdev(close, 20)` | −0.4746 | 0.5023 | 0.0316 | 0.7602 | −0.760 −0.419 −0.298 +0.032 −0.710 −0.680 −0.502 |
| `TS_BINENT_20` | 0.0096 | 0.0519 | 0.0307 | 0.1871 | −0.052 −0.043 −0.125 −0.141 −0.031 −0.046 +0.187 |
| `TS_PERMENT_20` | −0.0267 | 0.1181 | 0.0229 | 0.2617 | +0.150 +0.068 +0.118 −0.023 +0.262 +0.191 +0.106 |
| `TS_ABOVE_MEAN_20` | −0.0392 | 0.0640 | 0.0196 | 0.1654 | +0.035 −0.064 −0.136 −0.044 −0.091 +0.020 −0.165 |
| `TS_CROSS_MEAN_20` | 0.1390 | 0.2704 | 0.0416 | 0.4884 | +0.488 +0.270 +0.168 −0.042 +0.455 +0.373 +0.098 |
| `distinct / 20` (a variant, not a column) | −0.9946 | 0.9868 | 0.9268 | 1.0000 | −0.932 −0.987 −0.999 −1.000 −0.955 −0.927 −0.995 |

`TS_PERMENT_20` is worth a line because it was the one in-fork column
expected to see ties — permutation entropy folds them in — and it does
not: \|ρ\| 0.0229 … 0.2617.

### O2 — `LOT_ZERORET`, the nearest in-fork neighbour, and the exact relation

`LOT_ZERORET` counts **zero returns**, i.e. repeats between ADJACENT
closes; this column counts a repeat anywhere in the window. At length 19
the two read the same 20 closes (19 returns need 20 closes), and the
relation is a derivation rather than a correlation: a run of `k` zero
returns is `k+1` equal closes, all of which have a twin, so with `m` such
runs `count >= sum(k) + m >= sum(k) + 1`.

| frame | bound holds | of bars with a zero return | bars with NO zero return that still fire |
|---|---|---|---|
| grid-2tick | 1395 | 1395 | 86 of 86 |
| grid-10tick | 576 | 576 | 758 of 905 |
| grid-40tick | 263 | 263 | 574 of 1218 |
| grid-200tick | 19 | 19 | 116 of 1462 |
| range-bound | 1309 | 1309 | 172 of 172 |
| round-1000 | 1377 | 1377 | 104 of 104 |
| heavy-tailed | 882 | 882 | 380 of 599 |

The right-hand column is the difference between the two features: on
`grid-40tick`, 574 of the 1,218 bars with no zero return at all still read
non-zero, because the price came **back** to a level it had left. ⚠ At
length 20 the two read DIFFERENT windows (`LOT_ZERORET_20` needs 21
closes), so the bound does not hold there — a zero return between bars
T−20 and T−19 is counted by it and is invisible here. That is why the
bound is measured at 19 and the correlation at 20, which is the comparator
a default sweep reaches for.

### O3 — ⚠ pooling across tick regimes is not the per-frame figure

Four of §O1's seven frames are one path read at four price levels, so a
pooled correlation there partly measures which REGIME each frame sits in —
a level both this column and any other tick-grid column share. Pooling
seven frames of the SAME regime (price 1.00, seeds 11, 97, 5, 23, 44, 56
and 8 — written out rather than slash-joined, because five or more
slash-joined numbers is what
`tests/test_pine_coverage_csv.py::test_no_other_document_retypes_the_split`
reads as a verdict split, and it is right to)
takes that term out:

| comparator | same-regime pooled | same-regime per-frame median (range) | mixed-regime pooled |
|---|---|---|---|
| `LOT_ZERORET_20` | 0.6710 | 0.5185 (0.3178 … 0.6507) | 0.7962 |
| `LOT_ZERORET_60` | 0.7037 | 0.4991 (0.2219 … 0.6469) | 0.8427 |
| `stdev(close, 20)` | **−0.8862** | **0.7974** (0.6963 … 0.8533) | −0.4746 |
| `distinct / 20` | −0.9549 | 0.9266 (0.8422 … 0.9704) | −0.9946 |

**The mix inflates one pair and deflates another**, which is the reason to
report both rather than pick one. The zero-return pair looks like
DISCLOSE_GAP pooled across regimes (0.8427) and like SHIP within one
(0.7037 pooled, 0.4991 per-frame median); the `stdev` pair is the other
way round. The real-data anchors say the within-regime reading is the one
that carries: the screen measured the prototype at **0.7222** against the
engine's `stdev` over 89 real frames (top-5 per-frame max median 0.7700)
and bounded its whole fork sweep at **0.4851**, `LOT_ZERORET_60` included
by construction. Both of those are in the SHIP band, and both are close
enough to the 0.76 line that **Gate E on this module is what decides it**
— the synthetic numbers here cannot.

So the one-sentence summary of §O: this is **negative volatility measured
in ticks**, closest to a window dispersion measure (0.70 … 0.85 per frame
synthetic, 0.7222 real on the prototype), and distinct from the fork's own
zero-return share both in correlation (per-frame median ~0.50) and by the
derivation in §O2.

---

## L — the statistic itself

`python docs/measure_ts_reoccur_20.py L`.

### L1 — the level is set by the move in TICKS

Grid walks of 20,000 bars each, price 100 on a 0.01 tick, `sigma` chosen
so the bar's move is the stated number of ticks:

| ticks a bar | mean | sd | share reading 0 | share reading 1 | distinct |
|---|---|---|---|---|---|
| 1 | **0.9124** | 0.0724 | 0.0000 | 0.1872 | 12 |
| 2 | 0.7693 | 0.1237 | 0.0000 | 0.0163 | 18 |
| 3 | 0.6519 | 0.1487 | 0.0003 | 0.0015 | 20 |
| 5 | 0.4890 | 0.1589 | 0.0020 | 0.0000 | 19 |
| 10 | 0.2937 | 0.1434 | 0.0358 | 0.0000 | 15 |
| 20 | 0.1682 | 0.1201 | 0.1727 | 0.0000 | 15 |
| 50 | 0.0733 | 0.0830 | 0.4732 | 0.0000 | 11 |
| 100 | **0.0379** | 0.0620 | 0.6877 | 0.0000 | 9 |

Strictly decreasing, and the test pins the ordering plus the two ends
(> 0.85 and < 0.10) rather than the cells, because the frames are built
with dispatched kernels. The useful band is roughly 2 to 20 ticks a bar:
below it the column saturates near 1 and above it it degenerates toward a
binary flag.

### L2 — how long it remembers

Spearman of the column against its own lag:

| frame | lag 1 | lag 5 | lag 19 | lag 20 | lag 40 |
|---|---|---|---|---|---|
| grid-2tick | 0.9147 | 0.5928 | 0.1413 | 0.1666 | 0.1576 |
| grid-10tick | 0.9156 | 0.5985 | 0.0255 | 0.0276 | 0.0746 |
| grid-40tick | 0.9050 | 0.5826 | 0.0032 | 0.0071 | −0.0698 |
| grid-200tick | 0.9064 | 0.5588 | −0.0135 | −0.0213 | −0.0947 |
| range-bound | 0.9122 | 0.5816 | −0.0604 | −0.0654 | −0.0498 |
| round-1000 | 0.8974 | 0.5057 | 0.0461 | 0.0384 | 0.0186 |
| heavy-tailed | **0.9549** | **0.7761** | 0.3053 | 0.2992 | 0.2545 |

Windows one bar apart share 19 of 20 closes, hence the lag-1 figure; by
lag 19 the windows are disjoint and all but the heavy-tailed frame are at
or under 0.15. The heavy-tailed frame keeps 0.2992 at lag 20 because its
quiet stretches themselves persist — that is the data's memory, not the
window's.

### L3 — how far one close reaches

Bar T's close sits in the windows ending at T … T+19 and nowhere else, so
that is the whole reach. How many of those 20 bars actually move is not
fixed, because the duplicate count need not change:

| edit | bars moved | span relative to the edited bar |
|---|---|---|
| close[100] += 0.01 | 4 | (0, 3) |
| close[100] += 0.50 | 19 | (1, 19) |
| close[300] += 0.01 | 9 | (0, 19) |
| close[300] += 0.50 | 20 | (0, 19) |
| close[500] += 0.01 | 20 | (0, 19) |
| close[500] += 0.50 | 20 | (0, 19) |

The SPAN is the claim (never outside `[T, T+19]`, never empty); the COUNT
is measured and varies 4 … 20.

---

## W — what the dictionary keeps of the docstring

`python docs/measure_ts_reoccur_20.py W`. `gen_indicator_dictionary.py`
cuts the docstring's first paragraph for `docs/IndicatorDictionary.md`,
which CLAUDE.md sends a reader to before anything else — so the ⚠
warning has to survive that cut, or the one document a consumer reads
first says "it is a tick-grid feature:…" and stops.

⚠ **The cut is not "the first 150 characters".** It is
`d[:150].rsplit(" ", 1)[0] + "…"` (`gen_indicator_dictionary.py:294`):
a 150-character prefix and then the trailing word dropped **whole**. So
the usable length is **149**, not 150, and §W calls the generator's own
`desc()` rather than modelling it — an earlier draft of this section
modelled it as `d[:150]` and reported one character of slack that does
not exist.

| what | measured |
|---|---|
| the two sentences that must survive | **147** characters |
| what `desc()` returns | the two sentences, whole, plus `…` |
| the warning survives the cut | yes |
| characters the warning could still **grow** by | **2** |

The slack is found by growing the sentence until the generator's own
`desc()` loses it, not by subtracting from 150. **Two characters**:
lengthening those two sentences needs a re-run of §W and then of the
generator. (This paragraph has been wrong twice — first at "143
characters" for a 147-character sentence, then at "three characters of
slack" for two — which is why it is now measured through the function
that does the cutting.)

---

## E — Gate E

**Gate E: pending, run by issue-solver after this session.**

`docs/gate_e_ledger.csv` therefore has no row for `ts_reoccur_20`, and
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
reports it as owed — which is the expected state on the way to `dev`
(CLAUDE.md, "Owed, not failed"), since `ci.yml` and `gate-e-guard.yml` set
`GATE_E_PENDING_OK=1`. `tests/test_ts_reoccur_20.py::test_the_gate_e_row_is_owed`
asserts the row is ABSENT, so it fails the moment the receipt session
records it; replacing it with a test that pins the row's identity is part
of recording the row.

What the run owes this file:

1. the verdict under `r3-perframe-0.90` — pooled \|ρ\| and the top-5
   per-frame median, against the 687 comparators over the 89 ALTPORT-1
   frames;
2. **Gate C on real data**: the pooled fired and non-zero counts, which
   §C cannot supply. The question that matters is how much of the real
   universe sits in `grid-200tick`'s near-binary regime — on a frame where
   the column almost never fires, it carries almost no information
   however low its correlation is;
3. whether the port reproduces the screen's prototype figures. It should,
   and more strongly than this port's siblings did: §A1 measures the
   module **bit-equal** to the prototype on every frame, not merely
   rank-identical, so the only sources of difference on real data are the
   missing-data rule (§A4) and the harness.

If the run comes back STRUCK, the column is reverted and this file is kept
as the receipt — which closes #103 exactly as well as a ship.

---

## F — Gate F: the suites

| run | result |
|---|---|
| `python -m pytest tests/test_ts_reoccur_20.py -q` | **223 passed** |
| `python docs/measure_ts_reoccur_20_cpu.py` (the same module with `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`) | **223 passed** |

The reduced-dispatch run prints the features that survive, so the claim
cannot drift from what was turned off: `['SSSE3', 'SSE41', 'POPCNT',
'SSE42', 'AVX', 'F16C', 'AVX512CD', 'AVX512_CLX', 'AVX512_CNL',
'AVX512_ICL']`, and the script exits non-zero if any of the four named
features is still enabled.

`python docs/measure_ts_reoccur_20_cpu.py C` and `… L` also reproduce §C
and §L **to the printed digit** on this machine — every fired count,
distinct count, mean, histogram cell and autocorrelation. That is one
machine's answer and not a general one (a GitHub runner is different
hardware, which is the whole reason for the exercise), so the bands in
the tests stay bands.

Why that run matters here is the **frames**, not the module: this column's
arithmetic is one integer division and a pile of float equality tests,
neither of which a vector kernel can round differently, but the frames are
built with `np.exp`, `np.cumsum` and `np.round`, so a close can land on a
different grid point in the last bits. That is why every distinct-value
count, mean and Spearman in this file is pinned as a band or an ordering,
and why the exact counts (fired bars, bit-equality, emptied windows, the
back-dating) are the ones pinned to the digit — they are window geometry.

The full-suite figure is in the commit message rather than here, because
it moves with every other port in the tree.

---

## Z — cost

`python docs/measure_ts_reoccur_20.py Z`.

**Traced peak on 400,000 bars**, which does not GROW with `length` — the
sorted copy is taken `CHUNK_VALUES // length` rows at a time. ⚠ Not
"flat": at `length` 2 the whole 400,000-row frame is one chunk, below the
budget, which is why 2 reads 63% LOWER than the rest rather than higher:

| length | peak |
|---|---|
| 2 | 17.3 MB |
| 20 | 28.2 MB |
| 60 | 27.7 MB |
| 250 | 27.6 MB |

**Time**, on 100,000 bars, best of 3, three whole runs — the **fifth**
invocation of `section_Z`, and the last one run from the porting
session:

| run | length 2 | 20 | 60 | 250 | monotone | 250 / 2 |
|---|---|---|---|---|---|---|
| 0 | 6 ms | 16 ms | 29 ms | 121 ms | yes | 21.00× |
| 1 | 6 ms | 16 ms | 29 ms | 122 ms | yes | 21.19× |
| 2 | 6 ms | 16 ms | 29 ms | 121 ms | yes | 20.79× |

⚠ The milliseconds are this machine's and this run's and are not a claim,
**and neither are two significant figures of the ratio — that bracket has
now been broken three times.** Six invocations of this section on this
one worktree have printed, in order: 20.66 / 20.58 / 20.67, then 20.93 /
20.90 / 20.74, then 21.26 / 21.27 / 21.05, then 21.52 / 21.17 / 21.23,
then the table above, then 21.66 / 21.01 / 22.04 on a review re-run.
**Eighteen figures spanning 20.58 … 22.04**, and every bracket written
from the runs so far has been broken by the next one. What survives is
the **peak** (17.3 / 28.2 / 27.7 / 27.6 MB, to the digit on every
invocation that reported it, including the review re-runs), the
**monotone ordering** in `length` (True on all six runs of the two
invocations made from this session and on all three of the sixth), and
the ORDER OF MAGNITUDE: `length` 250 costs **about 20×** `length` 2. Anything tighter than that has failed a re-run here, twice,
and should not be written down again. The time grows faster than `length` because each window is sorted
in full: there is nothing to carry from one window to the next, since the
statistic reads a multiset rather than a sum. At the default `length` 20
the cost is 16 ms per 100,000 bars, and a BIST daily frame is ~4,500 bars.
