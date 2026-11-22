# C22-DFA measured — `c22_dfa`, catch22's DFA fluctuation scaling break (issue #128)

Every number here was produced by `python docs/measure_c22_dfa.py` on this machine
(numpy 1.26.4, pandas 2.3.3, pandas_ta 0.2.67b1+tu.1) during the porting session that
ran from 2026-11-20 into 2026-11-21 (the review folder is named for the day it
started). Section letters in brackets are the script's own, so each table can be
re-run on its own: `python docs/measure_c22_dfa.py A D`. The GPL-3.0 sections are
opt-in: `python docs/measure_c22_dfa.py P Q Q2 Q3 Q4 Q5 Q6 Q7`.

**Gate E: measured 2026-11-21 by issue-solver** on this tree (run
`is128-c22_dfa-c4c93c4d`): `C22DFA_100` pooled max \|ρ\| **0.07073344917219926**
vs `mad_pct_Pctl` (manifest, n = 389,949), per-frame max median
**0.07422100112784677** vs the same comparator over 89 frames → **SHIP** under
`r3-perframe-0.90`. §E has the full table and the ledger row; §E (context)
below it keeps the fork-overlap reading made HERE on six synthetic frames,
which is still not Gate E. Gate C's real-data limb is filled from the same
run: everything else in §C is synthetic.

---

## What the column is

    C22DFA_100 = (box sizes in the first piece of a two-piece log-log fit) / 21

Over the last 100 daily simple returns: z-score the window (inert, §A5), keep every
SECOND return starting from the oldest (the feature's lag of 2, so 50 points),
cumulatively sum them into a profile, and measure `F(tau)`, the root-mean-square
linearly-detrended fluctuation, over the 21 box sizes 5 .. 25. Fit TWO straight lines
to `log F` against `log tau`, sharing the scale at the break, choose the split that
minimises the summed squared residuals over the splits that leave at least
`max(8, round(21/4)) = 8` scales on each side, and report the share of the scales in
the first piece.

Three properties decide how it can be used, and all three are measured below:

1. **It takes six values and nothing between them** — 8/21 .. 13/21, i.e. 0.380952 to
   0.619048 (§A1). `prop_bounds(length)` derives the set at any `length`: 2 values at
   83, 6 at 100, 11 at 120, 19 at 250.
2. **The value at bar T does not read close[T]** (§B7). The decimation drops the
   window's newest return, so the VALUE at bar T is a function of closes
   `T-100 .. T-1`: causal, and one bar stale. ⚠ The NaN MASK is the exception and is
   still causal — the finiteness check and the noise floor run on the whole
   undecimated window, so a close at T that is NaN or zero blanks bar T (§B7b).
3. **Its "no break" level is the TOP of the range, not the middle** (§C4): on 400
   independent normal windows the median is 0.571429 and the commonest value is
   0.619048, 147 of 400.

---

## Gate A — correctness

Gate A does not start from the owner's prototype. It starts from the definition
catch22 names (`SC_FluctAnal_2_dfa_50_1_2_logi_prop_r1`, the hctsa operation
`SC_FluctAnal(y, 2, 'dfa', 50, 1, 2, 1)`, whose `prop_r1` output is the share of
scales in the first scaling regime) and from the paper's own one-line description,
"proportion of slower timescale fluctuations that scale with DFA (50% sampling)" —
the 50% sampling being the lag of 2. The reference implementation (pycatch22 1.0.2)
is **GPL-3.0** and this fork is MIT, so it is used only as a BLACK BOX, in sections P
and Q, and no shipped module imports it: §S counts the `.py` files under `pandas_ta/`
and how many of them import it — **399 and 0** — and a test asserts the same thing.

### A1. The ladder is a function of `length` alone

No data enters it, so the whole ladder of a given `length` is a constant.

| length | decimated points | scales | ladder | each side | values | bounds |
|---|---|---|---|---|---|---|
| 67 | 34 | 13 | 5 .. 17 | 8 | 0 | — (refused) |
| 80 | 40 | 16 | 5 .. 20 | 8 | 1 | 0.5 only |
| **83 = MIN_LENGTH** | 42 | 17 | 5 .. 21 | 8 | 2 | 0.470588 .. 0.529412 |
| **100 (default)** | 50 | 21 | 5 .. 25 | 8 | 6 | 0.380952 .. 0.619048 |
| 120 | 60 | 26 | 5 .. 30 | 8 | 11 | 0.307692 .. 0.692308 |
| 250 | 125 | 38 | 5 .. 62 | 10 | 19 | 0.263158 .. 0.736842 |
| 400 | 200 | 42 | 5 .. 100 | 11 | 21 | 0.261905 .. 0.738095 |

The six values at the default are `8/21` = 0.380952, `9/21` = 0.428571, `10/21` =
0.476190, `11/21` = 0.523810, `12/21` = 0.571429, `13/21` = 0.619048.

### A2, A3. The ladder, spelled twice, and the rounding

The vectorised ladder and the hand-spelled one agree at `length` 67, 100, 137 and
250. The rounding is `floor(x + 0.5)` (MATLAB's and C's `round`, half away from
zero), and it does not matter here: no step of the default ladder lands closer than
**0.002608** to a half, so numpy's round-half-to-even produces the same 21 integers.
That is measured, not assumed — it would change if the ladder did.

### A4. The definition re-spelled in plain Python

`math.fsum`, scalar loops, `np.polyfit` only for the order-2 variant. Over 200
windows of each of six 1,500-bar frames:

| frame | windows | bit-equal | max \|gap\| |
|---|---|---|---|
| walk | 200 | 200 | 0.0 |
| tick-rounded | 200 | 200 | 0.0 |
| penny | 200 | 200 | 0.0 |
| ar1 | 200 | 200 | 0.0 |
| cosine | 200 | 200 | 0.0 |
| student-t | 200 | 200 | 0.0 |

### A5. Every reading the definition leaves open, priced

366 windows sampled across the six frames. "moved" counts windows whose value
changes under that reading.

| reading | moved of 366 | max \|gap\| | Spearman vs shipped |
|---|---|---|---|
| lag: keep the LAST point of each pair (end-aligned) | 233 | 0.2381 | +0.3626 |
| lag: no decimation at all | 358 | 0.3619 | +0.3381 |
| cumulative sum BEFORE the decimation | 194 | 0.2381 | +0.5067 |
| ladder top from the RAW length | 358 | 0.3619 | +0.3789 |
| ladder rounded DOWN | 221 | 0.2381 | +0.6142 |
| ladder rounded UP | **0** | 0.0 | +1.0000 |
| score: sum of NORMS, not of squares | 100 | 0.2381 | +0.7677 |
| score: each norm over its own point count | 204 | 0.2381 | +0.3645 |
| pieces DISJOINT at the break | 167 | 0.2381 | +0.7199 |
| output `(break - 1) / ntt` | 366 | 0.0476 | +1.0000 |
| output `break / (ntt - 1)` | 366 | 0.0310 | +1.0000 |
| a flat floor of 6 scales each side | 181 | 0.3333 | +0.7176 |
| a flat floor of 7 | 147 | 0.2857 | +0.8237 |
| a flat floor of 9 | 211 | 0.1905 | +0.7598 |
| the fluctuation over the box's d.o.f. (`tau - 2`) | 51 | 0.2381 | +0.8993 |
| the leftover points off the HEAD, not the tail | 247 | 0.2381 | +0.3306 |
| the population z-score (`ddof` 0) | **0** | 0.0 | +1.0000 |
| NO z-score at all | **0** | 0.0 | +1.0000 |
| `q = 1` (mean absolute fluctuation) | 95 | 0.2381 | +0.8173 |
| per-box pooling instead of pooling every residual | **0** | 0.0 | +1.0000 |
| detrend order 2 | 259 | 0.2381 | +0.2464 |

**What is INERT, and why it is structural rather than lucky.** The whole feature is
invariant under `a * r + b` for any `a != 0`: a constant `b` in the returns is a
straight LINE in the profile and every box's own detrend removes it, and `a` scales
every residual of every box alike, which shifts `log F` by a constant and leaves the
residuals of both straight-line fits untouched. So the z-score and its `ddof` cannot
move an output, and §D4 measures the same invariance end to end. Per-box pooling is
inert for a different reason: at `q = 2` with equal box lengths, the mean of the
per-box mean squares and the mean over every residual are the same number. The ladder
rounded UP coincides with `floor(x + 0.5)` on this ladder.

### A6. The exact oracle, and how close the race is

The output is an INTEGER choice, so an oracle only has to get that integer right. The
window's returns are rationals and the feature is affine-invariant, so the oracle runs
on the RAW window: the profile, every per-box least-squares residual and `F(tau)**2`
are exact `Fraction`s — not one rounding — and only the logarithms and the two
straight-line fits are inexact, in 60-digit `Decimal`.

| frame | windows | break agrees | min margin | median margin |
|---|---|---|---|---|
| walk | 15 | 15 | 4.923e-03 | 6.779e-02 |
| tick-rounded | 15 | 15 | 6.868e-04 | 7.265e-02 |
| penny | 15 | 15 | **3.598e-04** | 8.496e-02 |
| ar1 | 15 | 15 | 1.149e-03 | 7.775e-02 |
| cosine | 15 | 15 | 1.828e-03 | 1.758e-01 |
| student-t | 15 | 15 | 4.264e-04 | 2.808e-02 |

90 of 90 sampled windows agree on the break. The margin is the relative gap between
the winning split's score and the runner-up's: **3.598e-04 at worst**, which is the
slack a reassociated numpy reduction would have to close before it could move an
output. That single number is why §D2 and §F1 come out as cleanly as they do.

---

## P, Q — the reference implementation as a black box (GPL-3.0, opt-in)

pycatch22 is GPL-3.0 and this fork is MIT. It is run here to MEASURE only — the same
use the owner's own screen prototype makes of it
(`docs/issues/screen/ind_screen_r3.py`) — and no line of it was read. ⚠ hctsa's own
source is not in this tree either: what these sections know about the definition's
open readings is what the reference's OUTPUT shows.

### P1. The shipped column against the reference, every window of six frames

| frame | windows | bit-equal | equal to 1e-12 | max \|gap\| | Spearman |
|---|---|---|---|---|---|
| walk | 1,400 | 1,400 | 1,400 | 0.0 | +1.0000 |
| tick-rounded | 1,400 | 1,400 | 1,400 | 0.0 | +1.0000 |
| penny | 1,400 | 1,400 | 1,400 | 0.0 | +1.0000 |
| ar1 | 1,400 | 1,400 | 1,400 | 0.0 | +1.0000 |
| cosine | 1,400 | 1,400 | 1,400 | 0.0 | n/a (constant) |
| student-t | 1,400 | 1,400 | 1,400 | 0.0 | +1.0000 |
| **TOTAL** | **8,400** | **8,400 of 8,400** | 8,400 | 0.0 | +1.0000 |

**0 disagreements.** Both take the same six values. So **this port IS the column the
2026-10-24 screen measured**, and the screen's Gate E figure (max \|rho\| 0.0707 vs
`mad_pct_Pctl`, SHIP) is an expectation that transfers — though it is still a figure
measured on the prototype, and Gate E is re-run on this port.

### P1b. Which reading the reference implements

1,680 windows (every fifth), scored by **23** named readings — every one the script
prices, pasted from the run, nothing omitted. The count is windows where that reading
equals the reference to 1e-12.

| reading | agrees of 1,680 |
|---|---|
| **shipped** (decimate-first, cumsum after, SQUARES, shared break, `max(8, round(ntt/4))` each side) | **1,680** |
| shipped, plain-Python spelling | 1,680 |
| the fluctuation over the box's d.o.f. (`tau - 2`) | 1,391 |
| score: sum of NORMS | 1,271 |
| `q = 1` | 1,264 |
| a flat floor of 7 scales each side | 1,053 |
| pieces disjoint at the break | 972 |
| a flat floor of 6 scales each side | 933 |
| cumsum before the decimation | 802 |
| end-aligned decimation AND cumsum before | 780 |
| score: norm per point | 693 |
| a flat floor of 9 scales each side | 688 |
| ladder rounded down | 681 |
| lag: end-aligned decimation | 611 |
| the leftover points off the HEAD | 596 |
| detrend order 2 | 495 |
| the curve linearly resampled onto an even log grid | 423 |
| the curve spline-resampled onto an even log grid | 265 |
| ladder top from the raw length | 34 |
| lag: no decimation | 21 |
| no decimation AND cumsum before | 21 |
| output `(break-1)/ntt` | 0 |
| output `break/(ntt-1)` | 0 |

The strongest rivals are the two that change the curve's SHAPE least: dividing the
pooled squares by the box's degrees of freedom (`tau - 2`), which shifts `log F` by
`0.5 log(tau / (tau - 2))` — small, and shrinking with `tau` — and scoring norms
instead of squares. Neither survives a 1,680-window sweep, and the `tau - 2` reading
moves the fewest windows of any reading in §A5 that moves one at all (51 of 366; four
others move 0 and are inert for the structural reasons §A5 gives). A reading can be
nearly right and still be a different column.

### Q, Q2, Q3. How the three structural readings were pinned

The first attempt at this port was **wrong, and a measurement caught it, not a
review.** It scored each split by the sum of the two residual NORMS and searched the
splits that leave 6 scales on each side — a defensible reading, and the obvious one if
"at least six points on each side" is what the definition means. It takes NINE values
where the reference takes six, and it piles on the two EXTREMES of its own range; the
reference's own histogram piles on 8/21 and 13/21, which is the boundary signature of
a narrower search. Agreement with the reference: 1,826 of 8,400 (21.7%).

So the readings were fitted to the reference as a black box:

* **§Q — 2,304 pipelines** over how the lag is applied (decimate keeping the first
  point / the last / not at all), where the cumulative sum goes, which ladder, four
  scoring rules, shared or disjoint pieces, six floors (`mp` 4 .. 9), two
  denominators and two offsets — 12 curves x 4 x 2 x 6 x 2 x 2 = 2,304. Best: 232 of
  294 — and every one of the top eleven rows agrees on the data pipeline
  (decimate-first, cumsum after, ladder from the decimated length), which is how that
  part was settled.
* **§Q2 — 560 pipelines** with the fluctuation's DIVISOR open (`boxes * tau`,
  `boxes * (tau - 1)`, `boxes * (tau - 2)`, `boxes * tau - 1`, `boxes`, 1, `tau`) and
  the leftover points off either end. The divisor turns out to be nearly inert:
  dividing by `boxes` instead of `boxes * tau` shifts `log F` by `0.5 log tau`, which
  is a LINEAR function of the regressor and therefore changes no residual at all (232
  of 294 for both). What is NOT inert is the `tau - 2` degrees-of-freedom reading (51
  of 366 windows move, §A5) and the leftover end (247 of 366).
* **§Q3 — 168 pipelines** with the even re-sampling (hctsa's own comment on this
  operation says the two-piece fit is preceded by a spline interpolation "to get an
  even sampling of the interval") and the search range open. Result:

| curve | score | pieces | range | agrees of 294 |
|---|---|---|---|---|
| **as measured** | **squares** | **shared** | **8 .. 13** | **294 of 294** |
| as measured | squares | shared | 8 .. 14 | 232 |
| as measured | squares | shared | 9 .. 13 | 210 |
| as measured | norms | shared | 8 .. 13 | 202 |
| as measured | squares | disjoint | 8 .. 13 | 171 |
| as measured | norms | shared | 8 .. 14 | 127 |

The spline- and linearly-resampled curves appear nowhere in the top 25, so hctsa's
interpolation comment does not describe what the reference does.

### Q4, Q6. The search range is a RULE, measured over every ladder size

8 and 13 are two numbers, not a rule. Feeding the reference windows of other lengths
gives it other ladders; its range is symmetric at every one of them (`lo + hi = ntt`
on all 32), so one number `a` describes it.

| scales | 16 | 17 | 21 | 26 | 31 | 33 | 34 | 37 | 38 | 41 | 42 | 45 | 46 | 47 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `a` seen | 8 | 8 | 8 | 8 | 8 | 8 | 9 | 9 | 10 | 10 | 11 | 11 | 12 | 12 |

(32 ladder sizes in all, 16 .. 47, from `length` 79 .. 1,187; the table shows 14 of
them. 47 is the largest ladder the feature produces under `length` 1,400.)

| rule | ladder sizes fitted | windows agreeing (§Q7) |
|---|---|---|
| **`max(8, round(ntt / 4))`, half away from zero** | **32 of 32** | **3,084 of 3,084** |
| `max(8, ceil(ntt / 4))` | 28 of 32 | 3,012 of 3,084 |
| `max(8, floor(ntt / 4) + 1)` | 24 of 32 | 2,945 |
| `max(8, ceil((ntt + 1) / 4))` | 24 of 32 | 2,945 |
| a flat 8 | 18 of 32 | 2,848 |
| `max(8, ceil(ntt / 4) + 1)` | 13 of 32 | 2,724 |
| `ceil(ntt / 4)` | 15 of 32 | 2,345 |

**§Q7 is the test that is not a fit**: the rule was fitted to the reference's observed
`lo`/`hi` only, and then the whole pipeline was run under each rule and compared with
the reference window by window, across every ladder size. The shipped rule predicts it
on **3,084 of 3,084** windows; every rival fails somewhere.

⚠ **The evidence has a ceiling even though `length` does not.** Those 32 ladder sizes
are 16 to 47 scales, i.e. `length` 79 to 1,187 — 47 is the largest ladder a
1,400-bar frame can produce here. Above that the rule is an extrapolation, and the
`length` argument's own documentation says so.

### Q5. The same reading, predicting the reference at other lengths

| length | scales | windows | bit-equal | max \|gap\| |
|---|---|---|---|---|
| 67 | 13 | — (this port refuses it) | — | — |
| 80 | 16 | 138 | 138 | 0.0 |
| 100 | 21 | 138 | 138 | 0.0 |
| 120 | 26 | 135 | 135 | 0.0 |
| 150 | 31 | 132 | 132 | 0.0 |
| 250 | 38 | 123 | 123 | 0.0 |
| 400 | 42 | 108 | 108 | 0.0 |

⚠ **One divergence from the reference, deliberate.** At `length` 67 the ladder has 13
scales and the rule leaves the search NO candidate; the reference returns **1.0**
there, a number outside the range the quantity can otherwise take. This port refuses
that regime instead: `MIN_LENGTH` is 83, the shortest `length` whose ladder gives the
search more than one candidate, and a smaller or missing `length` falls back to the
default (§H3). The 250 and 400 rows above were measured with the rule in place; the
first attempt at this port, with a flat floor of 8, disagreed with the reference on
31 of 123 and 25 of 108 windows there.

---

## Gate B — causality

### B1, B9. The future-perturbation sweep on the real module

Every close from bar J on is replaced by a fresh path; no bar before J may move.

| frame | gentle splice (2% vol), 8 splices | violent splice (20% vol, 3x jump) |
|---|---|---|
| walk | 0 of 35 offsets leak | 0 of 35 |
| tick-rounded | 0 of 35 | 0 of 35 |
| penny | 0 of 35 | 0 of 35 |
| ar1 | 0 of 35 | 0 of 35 |
| cosine | 0 of 35 | 0 of 35 |
| student-t | 0 of 35 | 0 of 35 |
| walk at `length` 83 / 120 / 250 | 0 of 35 each | — |

The violent splice exists because of §B4: this column reports ONE integer chosen by a
minimum over six candidates, and a gentle splice often fails to flip it. Measured on
the one-bar look-ahead mutant, the gentle sweep catches 5 of 35 offsets (7 with 32
splices) and the violent one 28 of 35.

### B6. The dependency map, measured one close at a time

The sharpest instrument here, because it does not depend on the sweep's power: perturb
EVERY close of the frame on its own and record which closes move bar T.

| bar T | factor | closes that move it | earliest | latest | any close >= T |
|---|---|---|---|---|---|
| 300 | x1.5 | 55 | 210 | 299 | **0** |
| 700 | x1.5 | 92 | 602 | 699 | **0** |
| 1,100 | x1.5 | 90 | 1,002 | 1,099 | **0** |
| 300 | x1.05 | 30 | 211 | 295 | **0** |
| 700 | x1.05 | 57 | 611 | 699 | **0** |
| 1,100 | x1.05 | 37 | 1,006 | 1,086 | **0** |

Every mover is in `[T-100, T-1]`. The count is below 100 because a tie absorbs the
rest: at x1.5, 55 to 92 of the hundred candidate closes change the integer.

### B7. The column at bar T does not read close[T]

Not a bug and not a look-ahead — it is what the lag does. The window ending at bar T
holds the returns of bars `T-99 .. T` and the decimation keeps every SECOND one
starting from the OLDEST, which drops the return of bar T itself.

| bar T | close[T] moves bar T | close[T] moves bar T+1 |
|---|---|---|
| 200 | no | yes |
| 500 | no | no (a tie) |
| 900 | no | yes |
| 1,300 | no | yes |

So the column is **causal and one bar stale**, and a consumer that pairs it with
same-bar features is pairing yesterday's reading with today's. It is in the module
docstring and in `docs/MLCompanionContract.md`.

### B7b. ... but the NaN MASK does read close[T]

The finiteness check and the noise floor run on the WHOLE undecimated window, which
includes the return of bar T. So:

| close[T] replaced by | bar T moves | bar T blanks | bar T+1 moves or blanks |
|---|---|---|---|
| x1.5 (finite) | 0 of 4 | 0 of 4 | 3 of 4 |
| NaN | 4 of 4 | 4 of 4 | 4 of 4 |
| 0 | 4 of 4 | 4 of 4 | 4 of 4 |

Neither half is a look-ahead — every close read is at or before T — and this is why a
single bad close blanks 101 bars starting AT its own bar (§H1) rather than 100
starting after it. A consumer recomputing the column on data truncated at T-1 gets
the same VALUES and a different MASK.

### B2. Fifteen mutants, read off the module's source, edited and exec'd in memory

| mutant | leaks (gentle) | leaks (violent) | bars moved on the walk | max \|gap\| |
|---|---|---|---|---|
| write-back-dated | 0 of 35 | 0 of 35 | 1,098 value / 2 mask | 0.2381 |
| window-one-ahead | 0 of 35 | 0 of 35 | 1,098 / 1 | 0.2381 |
| returns-rolled | 0 of 35 | 0 of 35 | 1,099 / 0 | 0.2381 |
| end-aligned-decimation | 0 of 35 | 0 of 35 | 1,099 / 0 | 0.2381 |
| **window-two-ahead** | **5 of 35** | **28 of 35** | 767 / 2 | 0.2381 |
| **window-ten-ahead** | **35 of 35** | **35 of 35** | 1,108 / 10 | 0.2381 |
| mask-back-dated | 0 of 35 | — | 0 / 0 (clean frame) | 0.0 |
| chunk-wide-demean | 0 of 35 | — | 0 / 0 | 0.0 |
| chunk-wide-sd | 0 of 35 | — | 0 / 0 | 0.0 |
| profile-across-rows | 0 of 35 | — | 0 / 0 | 0.0 |
| norms-not-squares | 0 of 35 | — | 391 / 0 | 0.2381 |
| no-overflow-guard | 0 of 35 | — | 0 / 0 | 0.0 |
| no-floor | 0 of 35 | — | 0 / 0 | 0.0 |
| no-zero-fluctuation-guard | 0 of 35 | — | 0 / 0 | 0.0 |
| no-either-guard | 0 of 35 | — | 0 / 0 (clean frame) | 0.0 |

⚠ **FOUR MUTANTS THAT LOOK LIKE LOOK-AHEADS ARE NOT, AND THAT IS THE SHAPE OF GATE B
FOR THIS COLUMN.** Back-dating the write, shifting the window one bar ahead, rolling
the returns and decimating from the newest end each move 1,098 to 1,099 of the walk
frame's 1,400 fired bars — so the edit lands — and each leaks on 0 of 35 offsets,
under the violent splice too, because each is still CAUSAL: a window shifted one bar
forward still ends on the return the decimation throws away. The mutant that IS a
one-bar look-ahead shifts the window TWO bars, so its kept set ends on the return of
bar T+1; it is caught. A sweep that "caught" the first four would be measuring
something other than causality.

⚠ **Four more are DEAD, each for a measured reason.** `chunk-wide-demean`,
`chunk-wide-sd` and `profile-across-rows` are all reads of other rows, and all three
are bit-equal to the real module on 1,500 bars of three frames: the affine invariance
of §A5 absorbs a chunk-wide mean or standard deviation, and a cross-row cumulative sum
adds a CONSTANT to a row's profile, which every box's own detrend removes. The fourth,
`no-overflow-guard`, is bit-equal because the zero-fluctuation guard blanks the same
rows (§H2).

A fifth, `mask-back-dated`, back-dates the bad-data MASK, so a clean frame cannot see
it: bit-equal on the walk, and caught on 12 of 12 offsets on a frame with one bad
close, moving exactly bar J-1 on each.

The remaining four — `norms-not-squares`, `no-floor`, `no-zero-fluctuation-guard`,
`no-either-guard` — are not look-aheads at all: they change VALUES, each has at least
one test of its own in `tests/test_c22_dfa.py`, and a causality sweep that caught them
would mean the sweep is measuring the wrong thing. (`norms-not-squares` is also the
reading §A5 and §Q3 price, so it is pinned twice: once as a mutant that moves 391 bars
and leaks on 0 of 12 offsets, and once as a plain-Python reading that disagrees with
the kernel on 100 of 366 windows.)

That is 2 + 4 + 4 + 1 + 4 = **fifteen**.

### B4. Why the sweep has the power it has

| frame | fired bars | distinct values | tie share | histogram |
|---|---|---|---|---|
| walk | 1,400 | 6 | 21.52% | 187 / 134 / 176 / 167 / 235 / 501 |
| tick-rounded | 1,400 | 6 | 20.30% | 217 / 139 / 149 / 153 / 257 / 485 |
| penny | 1,400 | 6 | 21.23% | 222 / 139 / 164 / 153 / 238 / 484 |
| ar1 | 1,400 | 6 | 35.31% | 214 / 197 / 157 / 150 / 224 / 458 |
| cosine | 1,400 | **1** | **100%** | 1,400 at 0.380952 |
| student-t | 1,400 | 6 | 20.73% | 219 / 147 / 137 / 131 / 213 / 553 |

(Histograms are counts at 8/21, 9/21, 10/21, 11/21, 12/21, 13/21.) The tie share is
the ceiling on what any perturbation sweep can see, and it is why the mutant catch
rates above are what they are rather than 35 of 35 everywhere.

---

## Gate C — reachability

The real-data limb is measured in §C5 below, from the launcher's Gate E run. §C1–§C4
are synthetic.

### C1. What fires

| frame | bars | fired | first fired bar | min | median | max | distinct |
|---|---|---|---|---|---|---|---|
| walk | 1,500 | 1,400 | 100 | 0.380952 | 0.571429 | 0.619048 | 6 |
| tick-rounded | 1,500 | 1,400 | 100 | 0.380952 | 0.571429 | 0.619048 | 6 |
| penny | 1,500 | 1,400 | 100 | 0.380952 | 0.571429 | 0.619048 | 6 |
| ar1 | 1,500 | 1,400 | 100 | 0.380952 | 0.523810 | 0.619048 | 6 |
| cosine | 1,500 | 1,400 | 100 | 0.380952 | 0.380952 | 0.380952 | 1 |
| student-t | 1,500 | 1,400 | 100 | 0.380952 | 0.571429 | 0.619048 | 6 |

### C2. The issue's own warning: tick rounding

> *"shape features of z-scored returns can pick up BIST tick rounding (many zero or
> repeated returns on low-priced stocks)"*

| frame | zero returns | share | fired | median | distinct |
|---|---|---|---|---|---|
| walk | 0 | 0.00% | 1,400 | 0.571429 | 6 |
| tick-rounded | 4 | 0.27% | 1,400 | 0.571429 | 6 |
| penny (2 lira, 1-kurus tick) | 210 | 14.01% | 1,400 | 0.571429 | 6 |

A seventh of the penny frame's returns are exactly zero and the column still fires
everywhere, takes all six values, and reads the same median as the continuous walk.
That is the synthetic half of the answer; the other half is Gate E's comparator list,
and the issue says what to look for there — a top comparator that is a price LEVEL
(`mcgd`, `ROLLING_LOW_250`) or `Volume` would point at tick rounding rather than at
return dynamics. §C5 answers it: the top comparator is `mad_pct_Pctl`, a percent
distance, not a price level or `Volume`, and at \|ρ\| 0.0707 it does not carry this
column either way.

### C3. What the column can and cannot separate

| frame | median | mean | histogram |
|---|---|---|---|
| iid walk | 0.571429 | 0.531701 | 187 / 134 / 176 / 167 / 235 / 501 |
| AR(1) in returns, phi +0.6 | 0.523810 | 0.522007 | 214 / 197 / 157 / 150 / 224 / 458 |
| AR(1) in returns, phi -0.6 | 0.523810 | 0.518367 | 211 / 192 / 183 / 186 / 216 / 412 |
| 20-bar cosine in returns | 0.380952 | 0.380952 | 1,400 / 0 / 0 / 0 / 0 / 0 |
| Student-t(3) | 0.571429 | 0.531667 | 219 / 147 / 137 / 131 / 213 / 553 |

⚠ **It does NOT separate persistent from alternating returns**: AR(1) at phi +0.6 and
at phi -0.6 both read a median of 0.523810 with similar histograms. What it does
separate is a periodic return series (one value, the bottom of the range) from a
stochastic one. A companion that wants the direction of the dependence wants
`tf_dfa_100` or `ts_ac1_60`, not this.

### C4. The iid centre, on 400 INDEPENDENT windows

| length | median | mean | histogram |
|---|---|---|---|
| 83 | 0.529412 | 0.502206 | 185 at 8/17, 215 at 9/17 |
| 100 | **0.571429** | 0.533452 | 52 / 41 / 40 / 55 / 65 / **147** |
| 250 | 0.605263 | 0.579605 | 19 values, 68 of 400 at the top one |

The commonest reading of iid returns is the TOP candidate, and the centre moves with
`length`. An iid fluctuation curve is close to one straight line, and a two-piece fit
of a straight line puts its break wherever the residuals happen to be smallest, which
on this ladder is biased towards the long-scale end.

### C5. Real data — measured 2026-11-21 by the Gate E run

Every count in §C1–§C4 is SYNTHETIC; this is the real-data limb, from run
`is128-c22_dfa-c4c93c4d` over the 89 frozen ALTPORT-1 BIST frames:

| | |
|---|---|
| pooled bars | 398,849 |
| `C22DFA_100` non-NaN | **389,949** |
| non-zero | **389,949** |

**389,949 of 398,849 bars fire (97.77%)**, and the 8,900 NaN bars are `89 × 100`
exactly — the warm-up (100 returns needed, so bars 0–99 of each frame), with
**0 further bars blanked**. non-zero equals non-NaN, so exactly 0.0 — reachable in
principle (§C1, only on the constant cosine frame) — was **not** read on any of
the 389,949 BIST bars.

---

## Gate D — scale-free

### D1, D2. Rescales

| case | result |
|---|---|
| x8, x64, 2\*\*-40, 2\*\*40 on each of six frames | **bit-identical** (24 of 24) |
| x10, x3.7, x0.1, x1.0000001 on the walk | **bit-identical** (0 moved bars, 0 mask) |
| re-based at 1e-6, 1e+6, 1e+100 | **bit-identical** |
| x8 at `length` 83, 120, 250 | **bit-identical** |

The exact-binary cases are by construction: the price enters only as
`c[t] / c[t-1]`, and `8a / 8b` is the double `a / b`. The INEXACT ones are not luck
either — the output is an integer choice whose runner-up is at least 3.598e-04 away
in relative score (§A6), so a perturbation that does not close that gap cannot move it
at all.

### D3. `0 < fires < n`

1,400 of 1,500 bars fire on every frame, and all six values appear on each of the five
stochastic ones, so a constant column could not pass. The 20-bar cosine frame IS
constant (one value on 1,400 bars) and is named as such everywhere it appears.

### D4. What it is blind to, and what it is not

| perturbation of the window | windows that move, of 200 |
|---|---|
| the returns x0.5 / x2 / x10 / x-1 | 0 / 0 / 0 / 0 |
| +0.001 / +1.0 on every return | 0 / 0 |
| the window REVERSED | 155 |
| the window SHUFFLED | 144 |

The first two rows are the affine invariance of §A5 measured end to end (the sign flip
included, because the fluctuation is even in the residuals). The last two say the
column reads the SHAPE of the series and not only its distribution.

---

## Gate E — measured 2026-11-21 by issue-solver → **SHIP**

Run `is128-c22_dfa-c4c93c4d`
(`gate_e_overlap.py run --module pandas_ta.statistics.c22_dfa`), made by the
launcher against this tree: 89 frozen ALTPORT-1 BIST frames, 398,849 pooled
bars, 329 `compute_all` + 358 `ml_features` manifest = **687** comparators
(the run's `n_degenerate` field reads 1), canary
`AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS bit-equal`, pandas 2.3.3 / numpy 1.26.4,
module sha1 `5d7070ff9768de6359b7a95384a5bfd9311018f7`, tree sha1
`6cba6c53f9dfc9ad27ad5770fa7a5e3284fb5f21`, data stamp
`1be6495ef7095ff67ad8f59a2fc0311d74f02652`.

| | `C22DFA_100` |
|---|---|
| pooled max \|ρ\| | **0.07073344917219926** |
| against | `mad_pct_Pctl` (manifest), n = **389,949** |
| top within `compute_all` | `natr_percentile` 0.05635671169373602, n = 389,949 |
| per-frame max median \|ρ\| | **0.07422100112784677** vs `mad_pct_Pctl`, 89 frames |
| frames with a per-frame median ≥ 0.90 | **0.0%** |
| non-NaN / non-zero | 389,949 / 389,949 (§C5) |
| bands | `r3-perframe-0.90` → pooled 0.0707 < 0.76 and 0.0742 < 0.90 → **SHIP** |

SHIP is the whole verdict: no column is removed, nothing is disclosed, no
waiver is needed. The row is in `docs/gate_e_ledger.csv` as
`c22_dfa,pandas_ta.statistics.c22_dfa,C22DFA_100,SHIP,…,is128-c22_dfa-c4c93c4d,2026-11-21`
with an empty waiver field, recorded by
`python docs/gate_e_ledger.py record … --measured 2026-11-21`, which refuses a
row whose module sha1 is not this tree's.

### E0. The prototype's figure, beside this port's

The 2026-10-24 screen measured the **prototype** — the GPL-3.0 reference's
column through pycatch22 (run `screen_r3_20261024`, same 89 frames, 398,849
bars, 687 comparators, canary bit-equal):

| | prototype, 2026-10-24 | this port, 2026-11-21 |
|---|---|---|
| pooled max \|ρ\| | **0.0707** | **0.0707** (0.07073344917219926) |
| against | `mad_pct_Pctl`, n = 389,949 | the same, n = 389,949 |
| top-5 per-frame max median | 0.0742 | 0.0742 (0.07422100112784677) |
| next comparators | `mad_pct_State` 0.0685, `Swing_Range_pct_Pctl` 0.0659 | `natr_percentile` 0.0564 is the `compute_all` top |
| fork overlap (stage 2, 12 frames, not Gate E) | 0.0620 vs `covariance:COV_30_1`, per-frame max median 0.0641 | not re-run (§E1 below is the in-fork reading made here) |

They agree to three decimals on the same top comparator and the same sample
size — §P1 is why that was expected: this port IS the column the screen
measured, 0 disagreements on 8,400 of 8,400 synthetic windows. The two runs
are still two runs, and the row above is the one that counts.

### E1. In-fork overlap, measured HERE (6 synthetic frames, not Gate E)

These are 1,500-bar synthetic frames, not the 89 frozen BIST ones, and the
comparators are this fork's own columns rather than the engine's `compute_all` ∪ the
`ml_features` manifest, so what follows is **not Gate E** and must not be quoted as
it. It is here because issue #128 names **#112 TF-DFA-100** as a relative and
that port SHIPPED after the 2026-10-24 screen, so the screen's own fork-overlap stage
never saw it. The table in the Gate E section above is the measurement that counts.

#### On the walk frame

| comparator | Spearman vs C22DFA_100 | bars |
|---|---|---|
| `TFDFA_100` (issue #112, the DFA exponent itself) | **+0.0702** | 1,400 |
| `C22AMI2_100` | +0.0598 | 1,400 |
| `TFAC1E_60` | +0.0539 | 1,400 |
| `LEANHURST_100` | +0.0387 | 1,400 |
| `TSAC1_60` | -0.0375 | 1,400 |
| `C22AMITIMESCALE_100` | -0.0370 | 1,400 |
| `TFSPECENT_64` | +0.0335 | 1,400 |
| `C22PERIODICITY_100` | -0.0048 | 1,400 |

#### Over six frames, the worst each comparator reaches

| comparator | worst \|rho\| | on |
|---|---|---|
| `TFDFA_100` | 0.1060 | student-t |
| `LEANHURST_100` | 0.1049 | penny |
| `TFAC1E_60` | 0.0948 | penny |
| `TFSPECENT_64` | 0.0859 | tick-rounded |
| `TSAC1_60` | 0.0610 | student-t |
| `C22AMI2_100` | 0.0598 | walk |
| `C22PERIODICITY_100` | 0.0434 | penny |
| `C22AMITIMESCALE_100` | 0.0370 | walk |

So the break and the exponent are not restatements of each other on synthetic data:
the DFA exponent `tf_dfa_100` is a continuous slope over box sizes 4 .. 10 of the
undecimated window, this is which of 21 box sizes a two-piece fit breaks at on the
lag-2-decimated one. (The cosine frame is constant here, so its Spearman is undefined
against every comparator.)

---

## G — frames with no fluctuation of their own, and the two blanking rules

### G1, G2. The noise floor (sd of returns at most 4096 eps = 9.09e-13)

| frame | sd of returns | shipped fires | with the floor removed |
|---|---|---|---|
| exactly geometric ladder (constant returns) | 1.175e-16 | **0** | 1,400, reading five of the six values |
| 1-ulp step at 1e6 on bar 700 | 5.733e-18 | **0** | exactly 100 (the windows holding the step) |
| one kurus a bar | 3.759e-06 | 1,400, all at 0.380952 | 1,400, unchanged |
| flat from bar 400 | 9.635e-03 | 399 | 399, unchanged |
| alternating +-2% | 2.000e-02 | 1,400 | 1,400, unchanged |

What the floor BUYS is that this column reads the SHAPE of a fluctuation curve, so
rounding noise would be read at full strength and a reader could not tell the result
from a price-shaped frame. What it COSTS on price-shaped data is nothing: 0 moved bars
and 0 mask differences against the unguarded spelling on each of six frames (§G2b).
⚠ It does **not** empty a deterministically smooth path — a price rising by exactly
one kurus a bar has a return standard deviation four million times the floor and fires
everywhere — so a companion must not assume the four catch22 ports blank together.

### G3. The zero-fluctuation guard, and that it is REACHED

`F(tau) == 0` has no logarithm. It needs the profile to be exactly straight inside
EVERY box of one scale, which a window of equal returns reaches — and the floor
already blanks that. The question is whether anything with real variation does, and
the answer is yes:

| construction | shipped fires | without the guard |
|---|---|---|
| returns constant in blocks of 5 | 1,400 | 1,400 |
| returns constant in blocks of 10 | 1,400 | 1,400 |
| returns constant in blocks of 25 | 1,400 | 1,400 |
| **returns exactly 0 then exactly +1% at bar 750** | **98** | **99** |

**§G3c locates it: bar 754**, whose profile is straight inside every box of 17 of its
21 scales — only 5, 7, 10 and 25 come out with `F > 0`. Unguarded it reads 0.380952,
a value. The guard also blanks the overflowing window of §H2. On price-shaped frames
it is inert: 0 moved bars and 0 mask differences on each of six.

---

## H — the NaN rules

| rule | measured |
|---|---|
| warm-up | the first `length` bars; the first fired bar is 100 |
| a close that is NaN, +inf, zero, negative or subnormal (1e-310) | 101 bars blank, exactly 700 .. 800 for a bad close at 700 |
| a close PAIR whose ratio overflows (1e-300 then 1e50) | 100 bars blank |
| a close PAIR whose SQUARES overflow (1.0 then 1e200) | 100 bars blank; with the `isfinite(sd)` limb removed, 0 of those 100 fire; with BOTH value guards removed, all 100 fire reading 0.380952 |
| a close pair of ratio 1e77 | 0 bars blank — the guard is not reached there |
| `length` below `MIN_LENGTH` (2, 50, 82) | falls back to `C22DFA_100` |
| `length` 83 / 120 | `C22DFA_83` / `C22DFA_120`, 1,417 / 1,380 fire |
| 100 closes | `None` (needs `length + 1`); 101 closes fire once |
| `offset=2` | shifts by two bars exactly |
| `fillna=-1` | fills the 100 warm-up bars |

⚠ **The `isfinite(sd)` limb is REDUNDANT here**, and that is the opposite of what the
same limb does in `c22_ami2`: a window whose sum of squares overflows z-scores to all
zeros, so its profile is flat and the zero-fluctuation guard blanks it anyway. It is
kept because it says what it means at the place the overflow happens, and the
measurement above is what says so.

---

## T, Z — cost and the chunk budget

| n | wall clock | traced peak | fired |
|---|---|---|---|
| 100,000 | 1.67 s | 16.2 MB | 99,900 |
| 400,000 | 6.81 s | 23.4 MB | 399,900 |

Chunk budgets of 100, 400, 999, the default `1 << 19` and 10\*\*9 (1, 4, 9, 5,242 and
10,000,000 rows per chunk) are **bit-equal**: every chunk is an independent run of
rows and nothing crosses one. Wall clock is not quoted as a band because it does not
reproduce.

---

## F — suites, and the other CPU dispatch

* `python -m pytest tests/test_c22_dfa.py -q` — **186 passed**.
* `python docs/measure_c22_dfa_cpu.py` — the same module with
  `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`, the list issue-solver
  re-runs port test modules under: **186 passed**. The script refuses to run if the
  environment edit did not take, and prints the dispatchable features still enabled
  (`SSSE3 SSE41 POPCNT SSE42 AVX F16C AVX512CD AVX512_CLX AVX512_CNL AVX512_ICL` on
  this machine).
* `python -m pytest -q` (the whole repository) — **2 failed, 13,677 passed, 86
  skipped** in 720.82 s, run on 2026-11-21 on the tree these review fixes produce
  (the module at 186 tests). The two failures are the expected ones and nothing else:
  `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (this
  port's Gate E row is owed, which is what the rules say happens until the launcher
  records it) and
  `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
  (needs the sibling `../AlternativeRepos` checkout; CI deselects it by name).
  An earlier run of the same command, before the review rounds and with the module at
  184 tests, gave 2 failed / 13,675 passed / 86 skipped — the same two failures and
  exactly two tests fewer. The launcher re-runs both repositories' suites in clean
  worktrees regardless.

### F1. Which digits move with the dispatch

Sections **A, B, C, D, E, G, H and Z** were re-run under the disabled dispatch and
compared table by table — every section of this receipt except §T, whose wall clock
and traced peak do not reproduce from one run to the next on either dispatch, and the
GPL-3.0 sections §P and §Q, which are a comparison against a C library and not a
reading of this module.

**One digit moves in all eight**: the standard deviation of the exactly geometric
ladder's returns in §G1, 1.175e-16 against 1.119e-16 — a figure that is pure rounding
noise and is quoted only to show it is below the floor. Everything else — every
count, every value, every margin in §A6, every bit-equality in §D, every leak count
in §B, every Spearman in §E — is identical under both dispatches.

That is not luck, and it is the reason this port can pin digits where its siblings
pin bands: the output is `break / scales`, a ratio of two small INTEGERS, and every
float in the pipeline exists only to decide which of six candidate splits minimises
one sum. A reassociated reduction has to close a relative gap of at least 3.598e-04
(§A6) before it can change an output.

---

## What is owed

| gate | state |
|---|---|
| A correctness | done — bit-equal to the reference on 8,400 of 8,400 windows, predicted on 3,084 of 3,084 across every ladder size, plus a plain-Python spelling and an exact-rational oracle |
| B causality | done — 0 of 35 offsets leak on six frames under both splice strengths, a one-close-at-a-time dependency map, and fifteen mutants |
| C reachability | done — synthetic limb plus real-data limb from the Gate E run: 389,949 of 398,849 pooled BIST bars fire |
| D scale-free | done — bit-identical under x8/x64/2\*\*-40/2\*\*40 and under x10/x3.7/x0.1/x1.0000001, `0 < fires < n`, not constant |
| E attribution | **done — SHIP.** Run `is128-c22_dfa-c4c93c4d`, 2026-11-21: pooled max \|ρ\| 0.0707 vs `mad_pct_Pctl`, per-frame max median 0.0742, both well under the `r3-perframe-0.90` lines |
| F suites | module green under both CPU dispatches; both repos' suites are the launcher's |
