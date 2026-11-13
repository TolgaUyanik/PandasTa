# TS-MEDSKEW-20 — `ts_medskew_20`, measured

Issue #98 (PandasTa), parent #31 ALPHASETS, screen of 2026-10-24.
Ported 2026-11-13 on branch `issue-98-ts-medskew-20`.

```
TS_MEDSKEW_20 = (mean(r) - median(r)) / sd(r)      20 simple returns,
                                                   sd with ddof=1
```

Source: tsfresh `feature_calculators` (MIT), `symmetry_looking`, as issue #98
states it — `symmetry_looking, continuous form: (mean-median)/std on 20
returns`.

Every number below comes from `docs/measure_ts_medskew_20.py` unless the line
says otherwise; the section letters (`A`, `B`, `C`, `D`, `G`, `O`, `Z`) are
that script's arguments. The tests that hold the same facts are in
`tests/test_ts_medskew_20.py` (207 of them).

**Gate E: pending, run by issue-solver after this session.** There is no row
in `docs/gate_e_ledger.csv` for this module yet, and
`tests/test_ts_medskew_20.py::test_the_gate_e_row_is_still_owed` asserts
there is none — that is the receipt session's cue. Gate C on REAL data is
owed from the same run; everything under §3 below is synthetic.

---

## 0. What the column is, in one paragraph

It is the **nonparametric skewness of a 20-return window** — Pearson's second
coefficient without its factor 3. The statistic is invariant to any affine map
of the returns with a positive slope, so it is neither a volatility nor a
direction column; it is continuous and nearly tie-free (1,480 distinct values
on 1,480 fired bars of a walk); it is bounded by `sqrt(19/20)` = 0.974679 by a
theorem, with 0.881631 the largest value any window built here reaches. **The
thing to read before using it is §O**: the fork shipped a backwards skewness
reading over the same 20 returns EARLIER THE SAME DAY (`TS_ABOVE_MEAN_20`,
issue #97, commit `6ace3dd`, merge `b99eeb5`, 2026-11-13), and the two
overlap at a pooled 0.8428 on real frames.

## 1. Gate A — correctness against the source formula

### A0 — what the oracle actually is

⚠ **The named source function does not contain this expression.** Published
`feature_calculators.symmetry_looking` is

```python
mean_median_difference = np.abs(np.mean(x) - np.median(x))
max_min_difference = np.max(x) - np.min(x)
return [(..., mean_median_difference < r["r"] * max_min_difference) ...]
```

— an absolute difference compared against a fraction of the RANGE, returning a
BOOLEAN. The continuous `(mean - median)/std` form is **issue #98's own
wording**, and the screen's prototype is its only prior implementation. So
Gate A starts from the issue's line, and the attribution is to the idea
(mean-against-median as a symmetry test), not to a line of tsfresh code.

How far apart the two are, on a 1,500-bar walk (A5):

| column | Spearman vs this one |
|---|---|
| `\|mean - median\| / (max - min)` — the literal `symmetry_looking` quantity | **−0.194171** |

Not a rescaling, not a near-copy: a different question. The sign flip comes
from the absolute value, which throws away exactly what this column keeps.

⚠ tsfresh is **NOT installed** in this worktree and web access is unavailable,
so nothing here is a read of tsfresh's own code;
`test_tsfresh_is_not_installed_here` records that so the claim cannot rot into
"checked against tsfresh".

### A1 — against the issue's formula applied window by window

A Python loop handing each window to `np.mean`, `np.median` and
`np.std(ddof=1)`; shares no code with the module (no `sliding_window_view`, no
pandas rolling). Nine 1,500-bar frames, 1,480 fired bars each, NaN masks
identical on all nine.

| frame | masks | shared bars | max \|difference\| |
|---|---|---|---|
| walk | identical | 1,480 | 1.11e-16 |
| tick-rounded | identical | 1,480 | 1.11e-16 |
| ar1+ | identical | 1,480 | 1.11e-16 |
| ar1− | identical | 1,480 | 1.11e-16 |
| heavy-tailed | identical | 1,480 | 1.11e-16 |
| right-skewed | identical | 1,480 | 1.11e-16 |
| left-skewed | identical | 1,480 | 1.11e-16 |
| two-point | identical | 1,480 | **2.22e-16** |
| trending | identical | 1,480 | 1.11e-16 |

Unlike the sibling `ts_above_mean_20`, this column is **not** a count, so
these are tolerances and not bit-equalities: a two-pass sd summed in a
different order is a different double.

### A2 — against a `math.fsum` scalar loop

Both sums by `math.fsum` (exact up to one rounding), the median spelt out on a
sorted copy: walk 1.11e-16, heavy-tailed 1.11e-16, right-skewed 1.67e-16, over
1,480 bars each with identical masks.

### A3 — against an EXACT rational oracle

Every float return is a rational, so the mean, the median and the VARIANCE are
computed in `fractions.Fraction` with no rounding at all; only the square root
and the final division round.

| frame | max \|difference\| | max relative |
|---|---|---|
| walk | 1.11e-16 | 1.449e-14 |
| tick-rounded | 1.11e-16 | 8.520e-14 |
| two-point | 3.33e-16 | 4.657e-16 |
| right-skewed | 1.67e-16 | 4.569e-15 |

### A3b — the one place the arithmetic is visibly lossy

A path whose returns have `|mean| / sd` = 1e5 (returns of 0.5 with an sd of
0.5e-5), where `mean - median` cancels five digits:

| | value |
|---|---|
| bars | 580 of 580, masks identical |
| bit-equal | 27 |
| max \|difference\| | **4.308e-11** |
| max relative | **1.305e-08** |

That is a factor of **3.9e+05** on an ordinary frame's 1.11e-16 — between five
and six orders of magnitude worse — and still **ten** orders below the
column's own [−0.88, +0.88] range (0.881631 / 4.308e-11 = 2.0e+10). The
relative pair divides the same way: 1.305e-08 / 8.520e-14 = 1.5e+05. Pinned by
`test_the_exact_oracle_on_the_worst_cancellation_this_file_can_build` so it
cannot get worse unnoticed. A market path does not look like this one; a
synthetic stress frame does.

### A4 — a closed form, not a recomputation

`n − 1` equal returns and one of `a` give mean `a/n`, median 0 and ddof=1 sd
`|a|/sqrt(n)`, so the column is **`sign(a)/sqrt(n)` whatever `a` is**:

| n | a | measured | expected | \|difference\| |
|---|---|---|---|---|
| 3 | +0.5 | +0.577350269189626 | +0.577350269189626 | 2.22e-16 |
| 3 | −0.5 | −0.577350269189626 | −0.577350269189626 | 2.22e-16 |
| 4 | ±0.5, +0.001 | ±0.500000000000000 | ±0.5 | 0 |
| 20 | ±0.5, +0.001 | ±0.223606797749979 | ±1/√20 | ≤ 2.78e-17 |
| 60 | ±0.5, +0.001 | ±0.129099444873581 | ±1/√60 | ≤ 2.78e-17 |

Windows whose mean and median agree read 0 to 2.2e-14 — `[+0.01, −0.01] × 10`
reads 5.95e-15, ten zeros then ten gains 2.16e-14, an arithmetic ladder
−1.76e-15. They are not exactly 0 because the closes are rebuilt from a
cumulative product, so the returns are not exactly the ones asked for.

### A5 — six readings the one-line formula leaves open, priced

On the same 1,500-bar walk, 1,480 shared bars each:

| reading | taken? | Spearman | max \|difference\| |
|---|---|---|---|
| simple returns vs LOG returns | simple | 0.999961 | 0.0109 |
| `ddof=1` vs `ddof=0` | ddof=1 (the prototype's `rolling.std`) | 1.000000 | 0.0109 |
| signed vs ABSOLUTE numerator (`\|mean−median\|/sd`) | signed | **−0.206800** | 0.8421 |
| with vs without the factor 3 | without | 1.000000 | 0.8421 |
| 20 RETURNS vs 20 CLOSES (19 returns) | 20 returns | 0.918816 | 0.3371 |
| of the returns vs of the CLOSES | of the returns | 0.123198 | 0.8916 |

The ABSOLUTE row is the reading the issue's line leaves open — only the sign
thrown away, the denominator untouched — and it is a different column from the
one in A0, which changes the denominator too: `|mean−median|/sd` reads
Spearman **−0.206800** against this one on the walk and is bit-equal on 642 of
1,480 bars — which is exactly the bars where this column is non-negative, since
`abs(v) == v` there. Both absolute forms land
in the same place: a column that cannot tell a left-skewed window from a
right-skewed one.

The `ddof` row is worth a sentence: the population sd is exactly
`sqrt(20/19)` = 1.025978352085 times the sample one at a fixed `length`, and
the measured ratio's min and max are both that number to twelve places. So a
rank miner cannot see the choice at all and a rule with a threshold can.

### A6 — the range, which is NOT [−1, 1]

`|mean − median| ≤ sd_pop` is a theorem: the median minimises `E|x − a|`, so
`|mean − median| ≤ E|x − median| ≤ E|x − mean| ≤ sd_pop` by Jensen. This
column divides by the **ddof=1** sd, which is larger by `sqrt(n/(n−1))`, so

```
|TS_MEDSKEW| <= sqrt((length - 1) / length)   = 0.974679 at length 20
```

What is actually attained:

| frame / family | max \|value\| |
|---|---|
| walk | 0.421042 |
| tick-rounded | 0.422317 |
| ar1+ / ar1− | 0.502387 / 0.503236 |
| heavy-tailed | 0.465991 |
| right-/left-skewed | 0.620183 |
| trending | 0.468938 |
| **two-point** | **0.881631** |
| 200,000 gaussian windows | 0.599473 |
| 200,000 exponential windows | 0.679401 |
| 200,000 lognormal(0, 2) windows | 0.735691 |
| 200,000 student-t(1) windows | 0.567221 |
| 200,000 two-point windows, random split | **0.881631** |
| 200,000 sorted-uniform windows, random levels | 0.802758 |

0.881631 is the parametric family `k` equal low returns and `20 − k` equal
high ones, maximised at **k = 11** (k = 12 gives 0.795822, k = 13 gives
0.715219). ⚠ Its neighbour is the trap: at **k = 10** the median sits between
the two levels and the column reads **0**, not the maximum. The gap between
0.881631 and the 0.974679 bound is **not** closed analytically here; the tests
assert the theorem and record 0.881631 as the largest value seen.

### A7 — against the screen prototype: the same column, same mask

The prototype (`docs/issues/screen/ind_screen.py`, candidate `ts_medskew_20`)
is `sdiv(mean(r, 20) - r.rolling(20).median(), std(r, 20))` — pandas' ONLINE
`rolling.mean()`/`rolling.std()`, the same rolling median, and `_fin` masking
non-finite values. No guards.

| frame | masks | shared | max \|difference\| | Spearman |
|---|---|---|---|---|
| walk | identical | 1,480 | 8.88e-16 | 1.000000 |
| tick-rounded | identical | 1,480 | 1.05e-15 | 1.000000 |
| ar1+ / ar1− | identical | 1,480 | 7.77e-16 / 1.28e-15 | 1.000000 |
| heavy-tailed | identical | 1,480 | **5.16e-15** | 1.000000 |
| right-/left-skewed | identical | 1,480 | 1.94e-15 / 9.99e-16 | 1.000000 |
| trending | identical | 1,480 | 4.61e-15 | 1.000000 |
| two-point | identical | 1,480 | 9.99e-16 | **0.999696** |

The two-point row is the one that is not 1.000000: there the column is heavily
tied and a last-bit difference reorders ties. On the walk, the set of bars one
reports and the other does not is **empty in both directions**, and a NaN
close at bar 200 leaves the same 1,459 of 1,500 firing for both.

Where they part company is the guards and locality:

* a 1%-a-bar geometric **ladder**: the prototype reports 280 windows, this
  module none (§G2);
* a planted giant return: the prototype's online accumulators move later bars
  by up to 0.42, this module's by 3.4e-14 (§G7).

Because Gate E's statistic is a Spearman over the bars where both fire, the
screen's prototype figures (max |ρ| 0.3727 vs `PVT_Slope_norm`, n = 396,970)
are **expected** to carry over. The launcher's run on THIS module is still the
number that decides ship or revert.

## 2. Gate B — causality, by mutant

Each mutant is the module's own source, read with `importlib`, one string
replaced, `exec`'d in memory. The blind sweep replaces every close from bar J
on and asks whether any bar BEFORE J moved; 37 offsets (40, 80, …, 1480).

**The real module leaks 0 of 37** on a walk, a tick-rounded walk and a
heavy-tailed path, and 0 of 37 at `length` 5, 60 and 250, with the first fired
bar exactly `length` in each case.

| mutant | what it breaks | live? | caught (walk / tick / heavy) |
|---|---|---|---|
| `back_date_two` | writes the output 2 bars early | yes | 37 / 37 / 37 |
| `back_date_full` | writes it `length − 1` bars early | yes | 37 / 37 / 37 |
| `forward_window` | windows read `np.roll(r, −1)` | yes | 37 / 37 / 37 |
| `forward_return` | `r[t]` reads `close[t+1]` | yes | 37 / 37 / 37 |
| `future_median` | the median is rolled one window | yes | **21 / 16 / 15** |

`future_median` is low because rolling the median by one window moves a bar
only when the two windows' medians differ enough to change it, which a splice
far from that bar need not do. The test bands it at 8–37 rather than pinning
it.

### The sixth mutant: the floor's own index, and where the blind sweep fails

`SHIFTED_FLOOR` rolls `hi`/`lo` by one window, so bar T's NaN mask reads
window T+1 — a genuine look-ahead. On a clean frame it is LIVE and moves
**exactly one bar, the last one**, measured as a set on all three frames:
`{1499}`. That bar is an `np.roll` **WRAP** (the rolled extrema of window 0,
which hold the undefined first return, land on the last window) and not a
look-ahead at all; `_caught` only inspects bars BEFORE an offset and the
offsets stop at 1,480, so the sweep scores **0 of 37** and proves nothing.

Two designed frames separate the two halves of the guard. Both are a walk
interrupted every 40 bars by 25 bars of a constant return:

| patch | interior bars emptied | …of which the unguarded spelling reports a finite value on | real module caught | floor mutant caught |
|---|---|---|---|---|
| constant **1%** returns | 216 | **213** | 0 of 37 | **35 of 37** |
| **exactly zero** returns | 216 | **0** | 0 of 37 | **0 of 37** |

The second row is the point. With exactly-zero returns the window's sd is 0,
the value is 0/0, and the `isfinite` backstop empties the bar whatever the
floor says — so the mutation changes nothing and the probe proves nothing. A
probe built the obvious way (the sibling port's zero patches) would have
passed this module **without testing the floor at all**. Both rows are pinned,
in `test_the_designed_probe_catches_the_floor_index_mutant` and
`test_exactly_zero_patches_do_not_catch_it_and_why`.

## 3. Gates C and D

### C — reachability (SYNTHETIC; the real-data counts are owed from Gate E)

Nine 1,500-bar frames, `length` 20, so 1,480 fired bars each:

| frame | fires | non-zero | distinct | range |
|---|---|---|---|---|
| walk | 1,480 / 1,500 | 1,480 | 1,480 | [−0.4210, +0.4013] |
| tick-rounded | 1,480 | 1,480 | 1,480 | [−0.4223, +0.4016] |
| ar1+ | 1,480 | 1,480 | 1,480 | [−0.5024, +0.4693] |
| ar1− | 1,480 | 1,480 | 1,480 | [−0.4857, +0.5032] |
| heavy-tailed | 1,480 | 1,480 | 1,480 | [−0.4660, +0.4502] |
| right-skewed | 1,480 | 1,480 | 1,480 | [−0.1457, +0.6202] |
| left-skewed | 1,480 | 1,480 | 1,480 | [−0.6202, +0.1457] |
| two-point | 1,480 | **1,478** | **385** | [−0.8816, +0.8816] |
| trending | 1,480 | 1,480 | 1,480 | [−0.4115, +0.4689] |
| flat (300 bars) | **0** | — | — | — |
| 1%-a-bar ladder (300 bars) | **0** | — | — | — |

`0 < fires < n` on all nine, and the column is continuous — every fired bar of
eight frames takes a distinct value. The two-point frame is the exception in
both columns: 385 distinct values and **2 exact zeros**, which are legitimate
readings (a window holding ten of each value has mean = median exactly), not
degenerate windows. On a walk there is no exact zero at all.

### D1 — ×8 and ×64 are bit-identical

Every input is a price RATIO and `8a / 8b` is the same double as `a / b`.
1,480 of 1,480 bars on each of the nine frames, at both factors, masks
included; and at other lengths on the walk: 1,497 (length 3), 1,495 (5),
1,440 (60), 1,250 (250).

### D2 — ×10, ×3.7 and ×0.1 agree too, though they need not

These perturb the returns in their last bits, so a bit-identity is not
available. Masks match exactly on all 27 frame/factor pairs; max |difference|
over all of them is **1.128e-13** (trending ×10), and the Spearman is
1.000000 everywhere except the two-point frame, where ties are reordered:
0.984689 / 0.985383 / 0.984065. The test asserts the masks exactly, the values
to 1e-12 and the rank correlation at > 0.95.

### D3 — stronger than a price scale: an affine map of the RETURNS

Both the numerator and the sd scale with the returns, and a shift cancels in
`mean − median`, so the whole statistic is invariant under `r → a·r + b` for
`a > 0`. Measured on a 1,500-bar gaussian-return frame, masks identical:

| map | max \|difference\| | Spearman |
|---|---|---|
| r × 2 | 2.68e-14 | 1.000000 |
| r × 0.5 | 3.95e-14 | 1.000000 |
| r + 0.004 | 2.74e-14 | 1.000000 |

That is why it reads ~0 against volatility and against direction (§O4).

### D4 — the floor is scale-invariant but NOT shift-invariant

`hi − lo` is unchanged by `r → r + c`, while the floor `4096 eps · max|r|`
grows with `c`. A frame whose returns span only the closes' own rounding:

| returns | median spread (as the module sees them) | floor | fires |
|---|---|---|---|
| ~1e-6 | 4.441e-16 | 9.095e-19 | **576 / 600** |
| the same + 0.004 | 4.441e-16 | 3.639e-15 | **0 / 600** |

The spread does not move at all; the floor moves by a factor of 4,000
(9.095e-19 → 3.639e-15), which is the ratio of the two return levels.
Only a window that close to the floor is affected — the nine frames of C are
not (§G1).

## 4. The guards, each priced in both directions

### G1 — what the floor costs

**0 body bars** on each of the nine clean frames: the module and the unguarded
spelling both fire on 1,480 of 1,500, and the set of bars the floor removes
after the warm-up is empty on every one.

### G2 — what it buys

A 1%-a-bar geometric ladder is a mathematically CONSTANT return that float64
reproduces only to rounding. The unguarded spelling reports **280 windows**
there, across **24 distinct values** spanning **[−0.3300, +0.3033]** — values
indistinguishable from a real reading, produced entirely by the last bits of
`(1.01)**k`. This module reports **none**. So does the prototype report them:
280 (§A7).

### G3 — the floor is RELATIVE, and that is a departure from the siblings

`statistics/ts_kurt_60.py`, `statistics/ts_binent_20.py` and
`statistics/ts_c3_20.py` floor an ABSOLUTE `4096 eps`. This module floors
`4096 eps · max|r|`, like `statistics/ts_above_mean_20.py`, because what needs
protecting is a difference of two centre readings against the rounding in
those centres, and that rounding scales with the window's own magnitude.

| frame | this module | an absolute `4096 eps` floor |
|---|---|---|
| returns of 1e-6 spread over 1e-13 (quiet but HONEST) | **580 / 600** | **0** |
| returns of 0.5 spread over 1e-14 (rounding, not data) | **0** | **0** |

"Honest" is itself a measurement, and §G3 prints it: the first frame's median
window spread is **3.648e-13** against a relative floor of 9.095e-19 — and
against the **4.441e-16** that the closes' own rounding produces at a return
level of 1e-6 (§D4), a factor of **8.2e+02**, so the data is nearly three
orders clear of the noise. The second frame is the mirror: median window
spread 3.575e-14 against a relative floor of 4.547e-13, i.e. BELOW its own
floor, which is why both spellings refuse it.

On the first frame the module agrees with the exact rational oracle to
**1.278e-09** over all 580 bars — **seven** orders worse than an ordinary
frame's 1.11e-16 (§A3), a factor of 1.2e+07, and still **nine** orders below
the column's range (0.881631 / 1.278e-09 = 6.9e+08). That is the price of
admitting a quiet window, and it is measured rather than assumed.

### G4 — the `isfinite` backstop has NO witness, and that is stated

`reported &= np.isfinite(value)` never fires on any input built here:

* over **14 frames** (the nine, flat, ladder, both patch frames and the quiet
  frame) there are **0 bars** where the floor reports and the value is not
  finite;
* the reason is arithmetic, not luck. The smallest non-zero return a close
  pair can produce is an ulp of 1.0 — **+2.220e-16** upwards, **−1.110e-16**
  downwards, so **1.110e-16** in magnitude. The floor only admits a window
  whose spread `s` exceeds `4096 eps · max|r|`, and the two extremes of such
  a window straddle its mean — `(hi − mean) + (mean − lo) = s` — so one of
  them is at least `s/2` away and the squared-deviation SUM is at least
  `(s/2)²`. At the smallest admissible `s` that is `(4096 eps · 1.110e-16
  / 2)²` = **2.549e-57**, against a smallest subnormal of 4.941e-324. 267
  orders of margin: `sd` cannot be 0 on a window the floor reports;
* an intended return path of 1e-100, 1e-150 or 1e-180 does not even exist —
  `1 + 1e-100` is `1.0`, so the module sees a frame of **one** distinct
  return, max |r| = 0, and fires on nothing.

It costs one pass over a `(rows,)` array and stays, labelled: the MUTANT
section above is where it does matter (B4's zero-patch row).

### G5 — the per-return magnitude bound

Every kept return satisfies `r**2 < max / (8 * length)`, so a window's squared
deviations — each at most `(2 max|r|)**2` — sum to at most half the float
maximum. The ceiling that puts on a return is **1.06e+153** at `length` 20.
Measured at the boundary (§G7): a planted return of 1e+154 or 1e+300 empties
the 20 windows holding it, and one of 1e+100 does not.

### G6 — a bad close empties exactly the windows holding it

A close that is NaN, infinite, zero, negative or subnormal spoils TWO returns,
so it empties the `length + 1` = 21 windows it sits in. On a 400-bar walk,
with **0 earlier bars moved** in every row:

| bad close at bar | 0 | 1 | 19 | 200 | 398 | 399 |
|---|---|---|---|---|---|---|
| bars emptied | 1 | 2 | 20 | **21** | 2 | 1 |

All five bad values behave identically: 359 of 400 bars fire, which is
400 − 20 warm-up − 21.

### G7 — one enormous return stays LOCAL, and the prototype's does not

A 2,000-bar frame priced at 1e-198 (so even the largest jump leaves every
close a normal float), one return planted at bar 200, compared with the
unspiked frame over the 1,780 bars from 220 on — bars whose windows no longer
contain the spike.

| spike | this module, max \|difference\| over bars 220+ | the 20 holding windows | their spread |
|---|---|---|---|
| ×1e+02 | 3.367e-14 | fire, median +0.223491 | 2.962e-04 |
| ×1e+06 | 3.089e-14 | fire, median +0.223607 | 2.963e-08 |
| ×1e+08 | 2.572e-14 | fire, median +0.223607 | 2.963e-10 |
| ×1e+100 | 2.670e-14 | fire, median +0.223607 | 1.388e-16 |
| ×1e+154 | 2.731e-14 | **empty** (above the bound) | — |
| ×1e+300 | 2.595e-14 | **empty** | — |

0.223607 is `1/sqrt(20)`, the closed form of A4: one odd return among nineteen
ordinary ones. ⚠ Those 20 windows are 20 DIFFERENT windows — the spike enters
and leaves, and the other nineteen returns differ — so the column reports
their median and their spread, not one value repeated. The spread is what
collapses as the spike grows: at ×1e+02 the ordinary returns are still
1.5e-04 of it and the windows span 2.96e-04; by ×1e+100 they span 1.39e-16. ⚠ The tail is **not** bit-identical, and cannot be — a spike
rescales every later close by a non-power-of-two factor, so `c[t]/c[t−1]` is
rebuilt from different bits. The number that matters is the comparison:

| spike | the PROTOTYPE, max \|difference\| over the same bars |
|---|---|
| ×1e+02 | 5.968e-10 |
| ×1e+06 | **1.326e-02** |
| ×1e+08 | **4.033e-01** |
| ×1e+100 | **4.176e-01** |

0.40 is a third of this column's whole range, on bars whose windows no longer
hold the spike. That is pandas' ONLINE `rolling.mean()`/`rolling.std()`, and
it is why this module reduces each window from its own values with
`sliding_window_view`. The rolling MEDIAN is kept, because a skip list only
compares and averages values — it accumulates nothing — and it is bit-equal to
`np.median(windows, axis=1)` on all 19,980 windows measured (§Z).

## O. In-fork overlap — what Gate E's 687 comparators cannot see

⚠ **This is the section to read before using the column.** Gate E's comparator
set is the Backtesting engine's `compute_all` ∪ the `ml_features` manifest; it
holds **no pandas_ta port**, so no Gate E run can measure this column against
the fork's own skewness columns.

### O1 — it IS a skewness reading

Over 20,000 independent 20-return windows drawn from a symmetric, a
right-skewed and a left-skewed law, against the windows' own bias-corrected
sample skewness: **Spearman +0.8803**, Pearson +0.8416.

Against `r.rolling(20).skew()` of the same frame, by frame — which is
*identically* `osap_retskew_21(close, length=20)`, the fork's shipped column at
this window, and the two rows came out equal to four decimals as they must:

| frame | ρ |
|---|---|
| heavy-tailed | **+0.8220** |
| two-point | +0.7165 |
| trending | +0.6906 |
| tick-rounded | +0.6651 |
| ar1+ | +0.6619 |
| walk | +0.6647 |
| ar1− | +0.5255 |
| right-/left-skewed | +0.2141 |

### O2 — against the two shipped neighbours

| frame | `OSAP_RETSKEW_21` | `TS_ABOVE_MEAN_20` |
|---|---|---|
| walk | +0.6485 | **−0.8885** |
| tick-rounded | +0.6491 | **−0.8894** |
| ar1+ | +0.6520 | −0.8854 |
| ar1− | +0.4933 | −0.8824 |
| heavy-tailed | +0.8028 | **−0.9025** |
| trending | +0.6690 | −0.8920 |
| two-point | +0.6982 | −0.7288 |
| right-/left-skewed | +0.2000 | −0.3941 |

`TS_ABOVE_MEAN_20` is issue #97's port — commit `6ace3dd`, merge `b99eeb5`,
**merged into this repo earlier on the same day as this port** (2026-11-13) —
and it is a BACKWARDS skewness reading over the SAME 20 returns, which is why
the sign is negative and the magnitude is high.

### O3 — the real-frame number, which exists and is adverse

The screen of 2026-10-24 measured both candidates on the 89 ALTPORT-1 BIST
frames and recorded the pair at **pooled 0.8428**. Three sources agree, and
none of them is a re-measurement by this session (which cannot reach
`../Backtesting`):

* `docs/issues/screen/cand_pairs.csv` line 39 of 56 —
  `ts_above_mean_20,ts_medskew_20,0.8428` — the screen's own candidate-pair
  file. ⚠ `docs/issues/` is gitignored, so this input exists in this worktree
  and on the owner's machine but is **not** in the repository; the two
  committed sources below are what a reader of the published repo has;
* `pandas_ta/statistics/ts_above_mean_20.py`'s docstring (line 179), which
  calls it "the most adverse figure on record for this column" — verbatim —
  and `docs/TsAboveMean20Measured.md` §5, which puts the pair's decision at
  "If issue #98 ships `ts_medskew_20`, these two columns need a decision".
  (The "pair to decide if it ever is" phrasing is
  `docs/MLCompanionContract.md`'s.)

The same screen file (`candidates.csv` line 82) is where this issue's own
Gate E prototype figures come from: 0.3726833336000077 vs `PVT_Slope_norm`
over the manifest at n = 396,970, top-5 per-frame max median
0.3693180708911093, verdict SHIP, fork overlap 0.259 vs `smi:SMI_5_20_5`.

Under the `r3-perframe-0.90` bands, 0.8428 is **DISCLOSE_GAP** (0.80 ≤ ρ <
0.90), not STRUCK. So, on the only real-frame measurement that exists, the two
columns are not a restatement at the 0.90 line — which is also what the
screen's own stage-2 fork overlap said about this candidate against everything
the fork shipped on 2026-10-24 (max |ρ| **0.2590** vs `smi:SMI_5_20_5`, 12
frames, per-frame max median 0.2436). ⚠ That stage-2 run predates BOTH
`osap_retskew_21` and `ts_above_mean_20` entering `Category`, so it cannot
bound either pair; the synthetic tables above are the only measurement of
those two pairs that exists.

⚠ **What this port makes STALE elsewhere, and could not fix.** The other half
of the 0.8428 pair says, in shipped API text, that this column does not exist:

| file | line | what it says |
|---|---|---|
| `pandas_ta/statistics/ts_above_mean_20.py` | 178 | "another skewness reading, **still a prototype and not shipped** (issue #98)" — assigned to `__doc__`, so `help(ta.ts_above_mean_20)` prints it |
| `docs/TsAboveMean20Measured.md` | 586-588 | "`ts_medskew_20` is **not shipped** … with no module in `pandas_ta/`. So it is not an in-fork overlap today" — one of three reasons that receipt gives for not reverting `TS_ABOVE_MEAN_20` |
| `docs/TsAboveMean20Measured.md` | 775 | "`ts_medskew_20` is still unshipped" |

All three are true up to this commit and false after it. **Neither file is in
this session's allowed-modify list** (issue #98's rules: modify `README.md`,
`docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`,
`docs/gate_e_ledger.csv`, `pandas_ta/__init__.py`, `pandas_ta/core.py`,
`pandas_ta/{category}/__init__.py`, `tests/test_altport2_ports.py`; add new
files only), so they are recorded here and in the commit message instead of
edited. `docs/MLCompanionContract.md` IS in that list and its copy of the same
clause carries a dated correction. **For the receipt session or the owner:**
the `ts_above_mean_20` docstring and §5 of its receipt need the same annotation
— append, do not rewrite, per that file's own "nothing struck, nothing
removed". Until then the sixth place a consumer could look says the opposite of
the five below.

**Where the disclosure reaches.** `CLAUDE.md` tells a reader to open
`docs/IndicatorDictionary.md` before judging a column, and
`gen_indicator_dictionary.py` builds that row's text from the first ~150
characters of the module docstring's opening paragraph. So the opening
paragraph was rewritten to put the overlap INSIDE those 150 characters, and
the generated row now reads "The NONPARAMETRIC skewness of the last `length`
returns. ⚠ Overlaps the shipped TS_ABOVE_MEAN_20 at 0.8428 on real frames.…".
Five places carry it: that row, the module docstring, the test module's
docstring (item 1), `docs/MLCompanionContract.md` and this section.

**The decision this port takes, and what would reverse it.** It ships, because
every band that has a real-frame measurement behind it says SHIP or
DISCLOSE_GAP: the screen's Gate E on the prototype (0.3727 vs
`PVT_Slope_norm`), the screen's fork overlap (0.2590), and the 0.8428 pair.
What would reverse it: the launcher's Gate E run on this module coming back
STRUCK, or the owner reading 0.8428 — two columns that answer "is this window
skewed?" twice — as a question-redundancy skip, which is a judgement the bands
do not make. `docs/EquivalentStrategies.md` is where that kind of ruling is
recorded; this receipt is the evidence for it.

### O4 — what it is not

On a walk: **+0.0800** against the same window's return standard deviation,
**−0.1129** against its mean return, **+0.0737** against the close itself.
Not volatility, not direction, not level — which is what D3's affine
invariance predicts.

### O5 — a state, not an event flag

Neighbouring windows share 19 of their 20 returns. Autocorrelation on a walk:
**0.8963** at lag 1, 0.6345 at lag 5, 0.3773 at lag 10, 0.1360 at lag 20.

### O6 — the level to expect

On independent windows of iid returns, 20,000 draws each:

| law | mean | sd | max \|value\| |
|---|---|---|---|
| gaussian | **−0.0006** | 0.1532 | 0.5927 |
| student-t(2) | −0.0002 | 0.1659 | 0.5045 |
| exponential | **+0.2832** | 0.1286 | 0.6727 |
| −exponential | **−0.2831** | 0.1280 | 0.6604 |

0 for any symmetric law (the reflection `x → 2u − x` preserves it and flips
the sign), and it moves off 0 only with skew. A heavy tail changes the spread,
not the centre.

## Z. Cost

400,000 bars, `tracemalloc` peak and wall clock on this machine:

| spelling | length 20 | length 250 |
|---|---|---|
| **this module** | 195 ms, **42.0 MB** | 536 ms, **42.0 MB** |
| deviation MATRIX (`(W - mean[:, None])**2`) | 215 ms, 76.9 MB | 726 ms, **812.4 MB** |
| `np.median(windows, axis=1)` | 237 ms, 90.0 MB | **1,759 ms**, 825.5 MB |

The module's peak is 42.0 MB at each of `length` 3, 20, 60 and 250 — it does
not grow with the window at all — and the call takes 104 / 195 / 266 / 536 ms
there. ⚠ Every wall-clock figure in this section is this machine's and moves
between runs — the window-by-window oracle below timed 0.81 s in one run of
the script and 0.73 s in another. The PEAKS are the claim.

Both rejected spellings are behaviourally equivalent, which is why the cost is
the whole argument: `np.median(windows, axis=1)` is **bit-equal on all 19,980
windows** of a 20,000-bar frame, and the matrix form agrees to 1.11e-16.
`tests/test_ts_medskew_20.py::test_the_deviations_are_spelled_column_by_column_not_as_a_matrix`
pins the spelling so neither one-liner can be restored without re-measuring.

The window-by-window oracle this was all checked against takes about 0.8 s on
20,000 bars where the module takes milliseconds, which is why it lives in
`docs/measure_ts_medskew_20.py` and not in the test module.

## F. Gate F — suites

* `tests/test_ts_medskew_20.py`: **207 passed**.
* The same 207 under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2
  FMA3"`, run by `docs/measure_ts_medskew_20_cpu.py`, which asserts the
  dispatch actually took and prints the features that survive (here `SSSE3`,
  `SSE41`, `POPCNT`, `SSE42`, `AVX`, `F16C`, `AVX512CD`, `AVX512_CLX`,
  `AVX512_CNL`, `AVX512_ICL`).
* Full suite in this worktree, default collection order:
  **3 failed, 7,274 passed, 85 skipped** in 183.5 s. The three failures are:
  1. `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
     — the one failure `CLAUDE.md`'s *Known breaks* section documents ("🔴 One
     test fails on a clean checkout");
  2. `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
     — not in that section; it is the test `CLAUDE.md`'s CI paragraph says is
     deselected by name because it needs the sibling `../AlternativeRepos`
     checkout;
  3. `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
     — this port's OWED Gate E row. Its message is exactly
     `no Gate E ledger row for ['mtd_ret', 'ts_medskew_20']`, `mtd_ret` being
     #206's, already owed on `dev`.
* ⚠ Pre-existing, unrelated, recorded rather than fixed: running
  `tests/test_wiring_accessors.py` BEFORE `tests/test_altport2_ports.py` in
  one process fails the pinned `CATEGORY_TOTAL` (328 against 331), because
  `pandas_ta/core.py:453` hands out the live `Category[name]` list and
  `core.py:692` removes names from it. Alphabetical collection hides it, so
  the full suite is green. This is the same defect recorded in commit
  `6ace3dd`.

## Wiring

| # | file | what |
|---|---|---|
| 1 | `pandas_ta/statistics/ts_medskew_20.py` | the indicator |
| 2 | `pandas_ta/statistics/__init__.py` | package export |
| 3 | `pandas_ta/__init__.py` → `Category["statistics"]` | discovery (330 → 331) |
| 4 | `pandas_ta/core.py` | `df.ta.ts_medskew_20()` |
| 5 | `tests/test_ts_medskew_20.py` | 207 tests |

Also: `README.md` (331 / 339 / statistics 40), `docs/IndicatorDictionary.md`
(regenerated), `docs/MLCompanionContract.md` (676 tagged columns, 318 `SF`),
`tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 331).
