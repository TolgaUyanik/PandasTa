# `lean_tdd_20` — measured

Issue #87 (LEAN-TDD-20), ported 2026-11-11 on branch `issue-87-lean-tdd-20`.
Column: **`LEAN_TDD_20`**, `pandas_ta/statistics/lean_tdd_20.py`.
**Status: SHIPPED through Gates A–F. Gate E measured 2026-11-11:
`DISCLOSE_GAP`, max \|ρ\| 0.8123 against `ui`. Nothing struck; the column
ships as wired.**

Every number in Gates A–D and the edge cases is printed by
`python docs/measure_lean_tdd_20.py` (pandas 2.3.3 / numpy 1.26.4) or by
`python -m pytest tests/test_lean_tdd_20.py -q`. The Gate E numbers, and the
real-data counts in Gate C, come from the issue-solver's harness run
`is87-lean_tdd_20-46cda3b2` and are quoted from its `overlap_max.csv` and
`meta.json`. Nothing in this file was typed from expectation; where a number
is *not* measured, the line says so.

## What it is

    r[t]     = close[t] / close[t-1] - 1
    s[t]     = min(r[t] - 0, 0)                 # 0 on an up or flat bar
    column   = sqrt( mean of s^2 over the trailing 20 returns )

The root-mean-square of a window's negative returns, with the up bars
counted as ZEROS rather than dropped — the denominator of the Sortino ratio.
The target (the minimum acceptable return) is **fixed at 0**, which is the
issue's parameter; see *A reading that is not offered as an argument* below.

The window holds 20 RETURNS, so the column reads 21 closes and the warm-up
is 20 bars. The value is dimensionless, non-negative, and **exactly 0.0** on
any window without a negative return.

## Source, and what "Apache-2.0 Lean" does and does not mean here

The issue names QuantConnect Lean's `TargetDownsideDeviation` (Apache-2.0)
and gives its parameters:

> Source: QuantConnect Lean indicators (Apache-2.0) — `TargetDownsideDeviation(20, 0)`

⚠ **Lean's C# source is not in this worktree and web access is unavailable.**
It was not read in this session. So the attribution is an attribution, not an
oracle: Gate A below is against the standard definition of the target
downside deviation — the RMS of the realised return's underperformance
against a target, with over-performance counted as zero underperformance —
plus the screen prototype's one line. Anything Lean does that neither says
(what it emits before its window fills, whether its divisor is the window
count or the number of shortfalls, what series it is fed) is **unverified
here**. The prototype
(`docs/issues/screen/ind_screen.py`, candidate `lean_tdd_20`, gitignored and
local to the owner's machine) was read and is used as a second
implementation, not as the source:

    np.sqrt(mean(ret(c).clip(upper=0) ** 2, 20))

## Gate A — correctness

**A1. Three hand-derived windows, exact doubles.** Derived from the formula,
with no implementation consulted; the module reproduces all three
**bit-for-bit**, not approximately
(`test_hand_derived_windows_are_exact`).

| closes | length | returns → squares | expected | module |
|---|---|---|---|---|
| `[8, 4, 2, 1]` | 3 | −0.5, −0.5, −0.5 → .25, .25, .25 | NaN×3, **exactly 0.5** | identical |
| `[100, 50, 100, 200, 100]` | 2 | −0.5, +1, +1, −0.5 → .25, 0, 0, .25 | NaN, NaN, sqrt(.125), **exactly 0.0**, sqrt(.125) | identical |
| `[100, 50, 100, 100]` | 3 | −0.5, +1, 0 → .25, 0, 0 | sqrt(0.25/3) = 0.288675 | identical |

`sqrt(0.125) = 0.3535533905932738` and `sqrt(0.25/3) =
0.28867513459481287`, both compared with `==`.

The second row is the one that matters most: a window with no down bar is
**0.0**, a reading rather than missing data. The third is the divisor
decision priced on a hand window — the shortfalls-only reading would say
`sqrt(0.25/1) = 0.5`, which is 2.113249e-01 away.

**A2. Against the screen prototype**, 1,500-bar walk, 1,480 fired bars:

| compared against | max \|diff\| | bit-equal | Spearman | NaN masks |
|---|---|---|---|---|
| the prototype retyped here | 0.000000e+00 | **1480/1480** | 1.00000000 | equal |
| **the screen's own registry candidate, imported from `docs/issues/screen/ind_screen.py`** | 0.000000e+00 | **1480/1480** | 1.00000000 | equal |

The imported row is the real candidate, not a retype: the measurement script
loads `REG["lean_tdd_20"]["fn"]` out of that file when the worktree has it,
and says so when it does not (a clone does not — `docs/issues/` is
gitignored). **Bit-equal** means the port is the column the screen's Gate E
numbers were taken on, so the issue's 0.8123 is about this code and not
about a near relative of it.

**A3. Against an independent per-window loop in plain Python scalars**, whose
window is summed by `math.fsum` (exact), 400 bars / 380 fired:

| frame | max \|diff\| | bit-equal | Spearman | NaN masks |
|---|---|---|---|---|
| walk | 1.734723e-18 | 304/380 | 0.99999995 | equal |
| the same walk rounded to 0.01 (0.50% zero returns) | 1.734723e-18 | 330/380 | 0.99999989 | equal |
| rally (every return up, every square exactly zero) | 0.000000e+00 | **380/380** | — (constant) | equal |

This is the only measured gap in Gate A, and it is `rolling.mean`'s
add-and-remove accumulation rather than the formula: an exact window sum and
pandas' online one differ in the last bits. 1.7e-18 against a column whose
values are ~1e-2 is 16 orders down. Note the Spearman is **not** exactly 1 —
a 1.7e-18 difference is enough to break an exact tie between two windows,
which is why the rank correlations NEAR 1 in this port — the ones an
"identical ranking" claim would rest on — are read at eight decimals
(0.99999995 rounds to 1.000000 at six and would read as "identical"). The
ones plainly below 1 are quoted at four to six.

**A4. The readings the wording leaves open.** Each decided and priced on two
frames — a continuous walk (seed 11) and the seed-55 walk rounded to 0.01
(0.27% of returns exactly zero) — over 1,480 fired bars:

| reading, and what this port does | frame | max \|diff\| | bit-equal | Spearman |
|---|---|---|---|---|
| the divisor is the WINDOW. Rejected: divide by the COUNT of returns that fell short, which is the same thing as DROPPING the up bars instead of counting them as zeros | walk | **1.180243e-02** | 0/1480 | **0.87067655** |
| | 0.01 grid | **1.937484e-02** | 0/1480 | **0.84520889** |
| the window holds `length` RETURNS. Rejected: `length` CLOSES, one return fewer | walk | 5.969723e-03 | 0/1480 | 0.96773254 |
| | 0.01 grid | 4.461599e-03 | 0/1480 | 0.96254305 |
| the mean of squares is divided by `length` (population). Rejected: `length - 1` | walk | 4.664010e-04 | 0/1480 | 0.99999999 |
| | 0.01 grid | 4.490337e-04 | 0/1480 | 0.99999999 |
| the warm-up is NaN. Rejected: a PARTIAL window — dividing by the window's current count, one plausible reading of an indicator that is not yet ready (and **not** a statement about Lean's code, which was not read here) | walk | 0.000000e+00 | **1480/1480** | 1.00000000 |
| | 0.01 grid | 0.000000e+00 | **1480/1480** | 1.00000000 |

Four things worth keeping from that table:

* **The divisor is the decision that matters.** 1.2e-2 on a column whose
  median is 1.0e-2, and Spearman 0.87: the shortfalls-only reading is a
  different feature, not a different rounding. It is also the reading with
  the wrong sign of response — under it, replacing a down bar with an up bar
  takes a term OUT of the average and can push the value up, where this port
  counts the up bar as a zero and the value falls.
* The returns-vs-closes reading is **not** only a different value: it fires
  one bar earlier (bar 19 against bar 20), because it reads one close less.
* The population-vs-sample divisor is a pure scale factor, sqrt(20/19) =
  1.025978, so it moves every value and almost no rank (0.99999999, and not
  1 only because a common factor applied in floating point still breaks
  exact ties). Pinned in
  `test_the_sample_divisor_is_a_different_value_and_the_same_ranking`, which
  also checks the ratio is constant to 1e-12.
* The partial-window warm-up agrees bit-for-bit on **all 1,480** fired bars.
  The whole difference is 19 head bars that this port leaves NaN and that
  reading fills with a differently-scaled statistic — which this fork's ML
  contract reads as data.

**A5. The spellings that are NOT readings.** Only `min(r, 0)` reaches the
square, so these three are the same column bit-for-bit on a walk, a 0.01
grid and a rally, over 1,480 fired bars each
(`test_the_spellings_of_the_shortfall_agree_bit_for_bit`, 9 cells, all
0.000000e+00 / 1480 of 1480):

| spelling | max \|diff\| | bit-equal (each frame) |
|---|---|---|
| `r.clip(upper=0)` — the prototype's | 0.000000e+00 | 1480/1480 |
| `np.where(r < 0, r, 0)` | 0.000000e+00 | 1480/1480 |
| `-((-r).clip(lower=0))` — the negated upside | 0.000000e+00 | 1480/1480 |

A zero return is not an edge case for this column: it contributes a zero
square whichever spelling is used, which is why the gridded frame (where
returns are exactly zero) agrees too.

**A6. Why there is no floor under the square root.** The squares are
non-negative, so the mean cannot be negative in exact arithmetic — but
`rolling.mean` adds and removes terms, and a mean a few ulps BELOW zero
would make `sqrt` NaN, turning "no downside at all" into missing data. That
possibility was measured rather than guarded against. Only the first frame
below exercises the dangerous path — a large square entering the window and
then leaving it; on the rally and the flat frame every square is zero from
the start (the `non-zero means` column), so the mean has nothing to cancel
and those two rows are a floor rather than evidence:

| frame | complete windows | means < 0 | means exactly 0 | non-zero means | column NaN on a complete window |
|---|---|---|---|---|---|
| one −50% bar, then only up bars | 180 | **0** | 160 | 20 | **0** |
| rally | 280 | **0** | 280 | 0 | **0** |
| flat | 280 | **0** | 280 | 0 | **0** |

Every emptied window is **exactly** zero rather than a small residue, so a
`clip(lower=0)` would be code nothing reaches. The claim is bounded: it is
measured on pandas 2.3.3 (which CI pins) and on these three frames, not
proved for every accumulation order, which is why
`test_a_complete_window_is_never_nan_however_the_squares_cancel` pins it —
a future pandas that returned a negative mean fails that test loudly instead
of emptying the column in silence.

## A reading that is not offered as an argument

The issue's second parameter is the minimum acceptable return —
`TargetDownsideDeviation(20, 0)` — and this port fixes it at 0, exposing only
`length`. (What Lean calls that argument is not verifiable here; the issue
gives two positional numbers and no name.) The reason is this fork's naming
rule: a column name encodes every parameter that changes its values, because
the parent repo's mined rules match on the string. A `target` argument that
did not appear in `LEAN_TDD_20` would let two columns ship under one name;
putting it in the name would change the name the screen, the dictionary and
the Gate E ledger all know. The issue asks for *target downside deviation,
target 0 (20)*, so the smaller scope is the faithful one. A non-zero target
is a new column with its own name, and the module's formula is written in the
general form so it is one line away.

## Gate B — causality, by mutant

Four mutants, each `importlib`-read from the module source and `exec`'d in
memory: the column back-dated by `length` (`write_shift`); the return taken
forward (`forward_return`); the squared shortfall taken forward
(`forward_square`); and a `center=True` rolling mean (`centered_mean`). Both
probes sweep **36 J values** (J = 60..1460 step 40) on 1,500-bar frames and
assert that nothing strictly before J moves. Every mutant is live on every
frame (its output differs from the real module's before any sweep runs).

**B1. The path sweep** — replace every bar from J onward with a different
path:

| | walk | walk vs rally | 0.01 grid | skewed down |
|---|---|---|---|---|
| **real module** | **0/36** | **0/36** | **0/36** | **0/36** |
| mutant: column back-dated by `length` | 36/36 | 36/36 | 36/36 | 35/36 |
| mutant: `px.shift(1)` → `px.shift(-1)` | 36/36 | 17/36 | 14/36 | 11/36 |
| mutant: the squared shortfall `.shift(-1)` | 36/36 | 17/36 | 14/36 | 11/36 |
| mutant: `center=True` on the one rolling mean | 36/36 | 36/36 | 36/36 | 31/36 |

The cells below 36 are the PROBE, not a safe mutant. This column is
ONE-SIDED: a positive return contributes the same zero square as the positive
return it replaced, so when the replacement path's `r[J]` is positive and the
original's was too, a one-bar-ahead mutant has nothing to show at bar J − 1.
The rally tail (every return positive) and the skewed path (90% of its bars
are small moves one way) are exactly the frames where that happens often.

**B2. The directed probe** — for each J, multiply every close from J onward
by **0.5**. A power of two divides out of every later return bit-exactly, so
exactly ONE return changes, and it becomes about −0.5, which is certainly a
shortfall. Measured premise, not assumed: `r[J]` is a new negative return at
36/36 J on every frame and **no other return moves at all** on any of them
(`test_the_directed_probe_changes_exactly_one_return_into_a_shortfall`).

| | walk | rally | 0.01 grid | skewed down |
|---|---|---|---|---|
| **real module** | **0/36** | **0/36** | **0/36** | **0/36** |
| mutant: column back-dated by `length` | **36/36** | **36/36** | **36/36** | **36/36** |
| mutant: `px.shift(1)` → `px.shift(-1)` | **36/36** | **36/36** | **36/36** | **36/36** |
| mutant: the squared shortfall `.shift(-1)` | **36/36** | **36/36** | **36/36** | **36/36** |
| mutant: `center=True` on the one rolling mean | **36/36** | **36/36** | **36/36** | **36/36** |

So all 16 directed cells are caught and all 8 real-module cells leak nothing.

The module has exactly **one** `.rolling(` call, so there is one window whose
causality needs pinning.

`offset` is the caller-reachable look-ahead and is pinned, not assumed:
`offset=2` is exactly the default shifted two bars later, `offset=-2` exactly
two bars earlier. The sweeps cover the default `offset=0`, which is what
`Category` uses.

## Gate C — reachability

**Real data, from the Gate E run** (`is87-lean_tdd_20-46cda3b2`, 89 frozen
ALTPORT-1 BIST frames, 398,849 pooled bars): `LEAN_TDD_20` is non-NaN on
**397,069** bars and non-zero on **397,065** of them. So it fires on 99.55%
of the pooled bars — the 1,780 NaN bars are the 20-bar warm-up × 89 frames
(1,780 exactly) — and only **4** of the fired bars are an exact zero, which
is a window with no down bar at all. The rows below are **synthetic**.

1,500-bar paths, 1,480 fired bars each (`fired`, `distinct` and `zeros` are
counted on the column; `zeros` means exactly 0.0):

| path | distinct | zeros | min | p10 | median | p90 | max |
|---|---|---|---|---|---|---|---|
| gaussian walk, sigma = 0.005 (seed 11) | 1093 | 0 | 0.001066 | 0.002360 | **0.003442** | 0.004639 | 0.006059 |
| gaussian walk, sigma = 0.015 (seed 11) | 1094 | 0 | 0.003187 | 0.007035 | **0.010251** | 0.013790 | 0.017953 |
| gaussian walk, sigma = 0.045 (seed 11) | 1093 | 0 | 0.009474 | 0.020802 | **0.030097** | 0.040138 | 0.051917 |
| AR(1) returns, φ = +0.8 | 1174 | 24 | 0.000000 | 0.003602 | **0.009389** | 0.018201 | 0.025918 |
| AR(1) returns, φ = +0.4 | 1141 | 0 | 0.001608 | 0.004855 | **0.007593** | 0.010341 | 0.015049 |
| AR(1) returns, φ = −0.4 | 1104 | 0 | 0.003135 | 0.006058 | **0.007902** | 0.009932 | 0.015114 |
| AR(1) returns, φ = −0.8 | 1119 | 0 | 0.004885 | 0.007796 | **0.011441** | 0.016884 | 0.025406 |
| gaussian walk, sigma = 0.005 (seed 101) | 1106 | 0 | 0.000659 | 0.002558 | **0.003667** | 0.004659 | 0.006362 |
| gaussian walk, sigma = 0.015 (seed 102) | 1149 | 0 | 0.002970 | 0.007119 | **0.010897** | 0.014370 | 0.019413 |
| gaussian walk, sigma = 0.045 (seed 103) | 1064 | 0 | 0.008916 | 0.019756 | **0.028066** | 0.037826 | 0.049628 |
| the seed-55 walk at 0.01 | 1119 | 0 | 0.003225 | 0.007505 | **0.010494** | 0.013564 | 0.017285 |
| rally, 300 bars (280 fired) | 1 | **280** | 0.000000 | — | **0.000000** | — | 0.000000 |
| flat, 300 bars (280 fired) | 1 | **280** | 0.000000 | — | **0.000000** | — | 0.000000 |

`0 < 1480 < 1500` fired on every 1,500-bar frame, so Gate D's non-constant
requirement is met with room — except on the rally and the flat frame, which
are genuine constant zeros and are the point of those two rows.

**The level is the volatility, scaled, and the two sigma triples say
different things.** The seed-11 triple is ONE set of standard normals scaled
by sigma (`measure_lean_tdd_20.py` passes the default `seed=11` to `walk`),
so its medians coming out 1 : 2.98 : 8.74 against sigmas of 1 : 3 : 9 is
close to an identity — the only departure is `exp`'s convexity on simple
returns, and that row is here because it is what the tests pin, not as
evidence. The seeds 101/102/103 triple is three INDEPENDENT draws, and that
is the evidence: medians 0.003667 / 0.010897 / 0.028066, ratios 2.97 and
2.58.

**The iid population value is sigma / sqrt(2)**, because for a symmetric
return `E[min(r,0)^2] = sigma^2 / 2`. Over **2,000 independent 20-return
windows** at sigma = 0.01 (population 0.007071): mean 0.006772, median
**0.006683**, sd 0.001752, p10 0.004564, p90 0.009094, above the population
value on 40.75%, finite on 2,000/2,000, and **0** of the 2,000 windows had
no down bar at all. The median sits 5.5% below the population value, which
is the downward bias of a square root of a mean on 20 observations — do not
read the column as an unbiased sigma/sqrt(2).

**What it adds over a standard deviation is asymmetry, and that is measured
rather than asserted.** Two 1,500-bar paths from the same two-point return
mixture, standardised to the same log-return sd and differing only in which
side the large moves fall on:

| path | realised simple-return sd | skew | column median | zeros | distinct |
|---|---|---|---|---|---|
| big moves DOWN | 0.01469475 | **−2.7975** | **0.014444** | 277 | 37 |
| big moves UP | 0.01532414 | **+2.7975** | **0.004555** | 0 | 93 |

Ratio of the medians **3.1712**, and note the direction of the volatility
difference: the up-skewed path is the slightly MORE volatile of the two by
realised sd, and still reads 3.17× lower. (The log returns are standardised
to 0.015 exactly by construction; the simple returns of the two paths differ
in sd because `exp` is convex, which is why both numbers are given.)

**It does not order persistence.** The four AR(1) rows above share ONE set of
innovations (seed 40), so the comparison is controlled, and the medians are
U-shaped in φ: 0.009389 / 0.007593 / 0.007902 / 0.011441 at +0.8 / +0.4 /
−0.4 / −0.8. That is the unconditional variance (σ²/(1−φ²), the same for ±φ)
and not a trend-against-reversion scale. `test_it_does_not_order_persistence`
pins it so nobody reads this column the way `lean_hurst_100` or
`lean_momersion_20` are read.

**Against realized volatility** on the seed-11 walk, 1,480 bars:

| compared against | Spearman |
|---|---|
| the population sd of the SAME 20 returns | **0.63558358** |
| `stdev` of the closes (a price-level dispersion, not a return one) | 0.145771 |

and the median ratio of the column to `sd / sqrt(2)` is 1.014690. So on a
symmetric synthetic frame the column shares about the level of 20-bar
realized volatility and keeps a good deal of its own rank information; the
real-data figure that matters is Gate E's, and this port's own Gate E run put
it at 0.8123 against `ui` (DISCLOSE_GAP).

**Drift moves the level, and barely the ranks.** Walk vs the same walk at
+0.004 of log drift a bar: max \|difference\| **3.121724e-03**, 0 of 1,480
bars bit-equal, Spearman **0.99144748**, NaN masks equal, and the drifted
median is lower (drift makes down bars rarer and smaller).
`test_drift_moves_the_level_but_barely_the_ranks` pins all three parts.

**Nearest shipped columns on ONE 1,500-bar synthetic OHLC frame — NOT Gate
E** (11 shipped columns, one frame; Gate E is 687 comparators over 89 frozen
BIST frames):

| \|ρ\| | signed | column | n |
|---|---|---|---|
| 0.6798 | +0.6798 | `ui` (Ulcer Index) | 1,474 |
| 0.5847 | −0.5847 | `rsi_14` | 1,480 |
| 0.5454 | −0.5454 | `zscore_30` | 1,471 |
| 0.5425 | −0.5425 | `entropy_20` | 1,462 |
| 0.5303 | +0.5303 | `natr_14` | 1,480 |
| 0.1504 | −0.1504 | `skew_30` | 1,471 |
| 0.1458 | +0.1458 | `stdev_20` (of CLOSES) | 1,480 |
| 0.0623 | +0.0623 | `lean_hurst_100` | 1,401 |
| 0.0451 | −0.0451 | `kurtosis_30` | 1,471 |
| 0.0097 | −0.0097 | `chop_14` | 1,480 |
| — | — | `lot_zeroret_60`: constant on this frame, no rank correlation defined | 1,440 |

The n differ by each comparator's own warm-up, so these eleven are not on
identical footing: the ranking is indicative, and the only overlap figures
that decide anything are Gate E's.

`ui` and `natr` lead, which is the same pair the issue's prototype screen
found on real data (`ui` 0.8123, `natr` 0.7332) — on one synthetic frame at
two thirds of the real-data level. `stdev_20` is low only because it is the
dispersion of PRICES, not of returns; the return-sd comparison above (0.6356)
is the fair one.

## Gate D — scale-free

1,500-bar frames, 1,480 fired bars each. **x8 and x64 are bit-identical** on
all three frames, because `8a / 8b` is the same double as `a / b`, so every
square, window mean and root is the same bit pattern:

| rescale | walk | the seed-55 walk at 0.01 | skewed-down path |
|---|---|---|---|
| ×8 | **1480/1480** | **1480/1480** | **1480/1480** |
| ×64 | **1480/1480** | **1480/1480** | **1480/1480** |

max \|diff\| 0.000000e+00 and NaN masks equal on all six.

**x10 and x3.7 are NOT bit-identical, and here is how far they move.** A
factor that is not a power of two does not divide out of
`fl(k·a) / fl(k·b)`, so the return itself changes in its last bits:

| frame | rescale | max \|diff\| | max relative | bit-equal | Spearman |
|---|---|---|---|---|---|
| walk | ×10 | 7.112366e-17 | 1.009365e-14 | 55/1480 | 0.99999999 |
| walk | ×3.7 | 6.071532e-17 | 7.263854e-15 | 107/1480 | 0.99999999 |
| 0.01 grid | ×10 | 4.510281e-17 | 6.629129e-15 | 96/1480 | 0.99999999 |
| 0.01 grid | ×3.7 | 6.938894e-17 | 1.218341e-14 | 112/1480 | 0.99999999 |
| skewed down | ×10 | 4.510281e-17 | 2.547723e-15 | 804/1480 | **0.99305976** |
| skewed down | ×3.7 | 3.816392e-17 | 2.547723e-15 | 826/1480 | **0.99441820** |

NaN masks agree on all twelve. The skewed rows are the honest part of the
claim: that column takes only **37 distinct values** (a two-point mixture
gives few distinct window sums), so a 4.5e-17 difference BREAKS EXACT TIES
and the rank correlation drops to 0.9931 although no value moves by more
than 4.6e-17. On a frame with no ties the ranking survives at 0.99999999.
`test_a_non_power_of_two_price_scale_agrees_to_rounding` carries the rank
floor as a per-frame parameter for that reason, rather than one constant
pretending the two cases are the same.

`0 < fires < n`: 0 < 1,480 < 1,500 on the walk, with **1,094 distinct
values** and 0 exact zeros, so the column is not a constant.

## Gate E — attribution

**Measured 2026-11-11 by the issue-solver's run `is87-lean_tdd_20-46cda3b2`**
(`gate_e_overlap.py run --module pandas_ta.statistics.lean_tdd_20`, default
parameters, `kwargs {}`), on the 89 frozen ALTPORT-1 BIST frames, 398,849
pooled bars, against 687 comparators (329 `compute_all` + 358 `ml_features`
manifest `1d`), 1 of them degenerate on this universe. Canary: AKBNK.IS,
BIENY.IS, AGHOL.IS, SASA.IS **bit-equal**. pandas 2.3.3 / numpy 1.26.4;
module sha1 `fd1785de`, tree sha1 `e3c3ea01`, data stamp `1be6495e`.
Verdict schema `r3-perframe-0.90`.

| column | max \|ρ\| | against | set | n | per-frame max median | frames | frames ≥ 0.90 | verdict |
|---|---|---|---|---|---|---|---|---|
| `LEAN_TDD_20` | **0.8123** | `ui` | compute_all | 396,535 | **0.8020** (`ui`) | 89 | **0.0%** | **DISCLOSE_GAP** |

Exactly: pooled 0.8122808091846513, per-frame max median 0.8019944862566607.
The strongest comparator in the manifest half is `Stop_2ATR_pct` at
**0.7332** (0.7332026530163992, n = 397,069) — which is the issue's third
listed comparator, and under the 0.76 ship line on its own.

**Verdict: DISCLOSE_GAP, so the column ships and the overlap is disclosed.**
`CLAUDE.md`'s Gate E row strikes a column at pooled \|ρ\| ≥ 0.90 or a top-5
comparator's per-frame median ≥ 0.90; this is 0.8123 and 0.8020, so **0.0877
and 0.0980 below the two strike lines** and inside the 0.80 ≤ ρ < 0.90
disclose band. Nothing was struck, and nothing was removed from the port.
What is disclosed is the thing the module docstring and Gate C already say in
their own words: **on real data this column is mostly 20-bar volatility**,
and the shipped column it most nearly restates is `ui`, the Ulcer Index.
A miner that already holds `ui` holds something whose rank agrees with this
column at ρ = 0.81 pooled and at a median of 0.80 per frame, which is close
enough that the two should be read as near-neighbours rather than as two
independent risk features.

**The port's run reproduced the screen's prototype numbers.** The screen
(2026-10-24, run `screen_20261024`) measured the prototype at max \|ρ\|
0.8123 vs `ui` over n = 396,535 with per-frame max median 0.8020 — the same
three figures as the port's run above, and the same comparator. That is the
consequence of Gate A2, where the port is bit-equal to the screen's own
registry candidate on 1,480 of 1,480 fired bars: the screen's numbers were
about this code.

Recorded in `docs/gate_e_ledger.csv`
(`python docs/gate_e_ledger.py record … --measured 2026-11-11`) as row
`lean_tdd_20,pandas_ta.statistics.lean_tdd_20,LEAN_TDD_20,DISCLOSE_GAP`. The
row carries no waiver, because only a STRUCK row needs one.

## Gate F — suites

Run in this worktree. The port session's runs are kept because they are what
Gates A–D were read off; the receipt session's runs are the current state.

Port session (2026-11-11, Gate E still owed):

* `python -m pytest tests/test_lean_tdd_20.py -q` → **109 passed** in 3.05 s.
* `python -m pytest -q` → **3 failed, 5679 passed, 83 skipped** in 119.57 s,
  the last full run of that session (the earlier ones gave the same three
  counts, except for one run in which the review log also tripped
  `test_pine_coverage_csv.py::test_no_other_document_retypes_the_split` by
  writing five counts slash-joined; that is fixed and the log says so).
  The third failure was
  `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
  then owed for `['lean_tdd_20', 'mtd_ret']`.

Receipt session (2026-11-11, after the Gate E row was recorded):

* `python -m pytest tests/test_lean_tdd_20.py -q` → **109 passed** in 2.89 s.
* `python -m pytest -q` → **3 failed, 5686 passed, 83 skipped** in 120.99 s.
  The passed count is **7 higher** than the port session's, and the 7 are
  the new ledger row's own parametrized cases in `tests/test_gate_e_ledger.py`:
  that module parametrizes over the live rows four times
  (`test_row_names_the_module_that_defines_the_indicator`,
  `test_row_still_describes_its_module`, `test_row_output_has_not_moved`,
  `test_struck_rows_carry_the_waiver_for_this_exact_measurement`), over all
  rows twice (`test_verdict_follows_the_bands`,
  `test_every_column_fires_on_real_data`) and over the indicators named by
  live rows once (`test_ledger_columns_are_the_default_output`) — 4 + 2 + 1
  for one added row.

The failures are the same three in both runs, and `lean_tdd_20` is no longer
one of their causes:

1. `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
   — needs the sibling `../AlternativeRepos` checkout, deselected in CI
   (`CLAUDE.md` "Known breaks").
2. `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` — the
   `supertrend` citation into the untracked `docs/pine/`, the second
   "Known break".
3. `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` —
   now reports `no Gate E ledger row for ['mtd_ret']`, measured in the
   receipt session. `lean_tdd_20` has dropped off that list; `mtd_ret` is an
   unrelated indicator whose row was owed before this branch and is not this
   issue's to record.

The launcher runs both repos' suites in clean worktrees.

## Edge cases, measured

| case | behaviour |
|---|---|
| 20 bars | returns `None` (`verify_series` floor: 20 returns need 21 closes) |
| exactly 21 bars | fires 1/21, at bar 20 |
| rally, 300 bars (every return up) | fires 280/300, every value **exactly 0.0** |
| exactly flat, 300 bars | fires 280/300, every value **exactly 0.0** — a flat window has no shortfall, so it is zero rather than NaN |
| one NaN close at bar 200 | empties exactly 21 bars, 200..220; **2** later bars (222 and 225) then move by at most **3.469e-18** (2.449e-16 relative) |
| one zero / negative / infinite / subnormal (1e-310) close | each empties the same 21 bars and moves the same 2 later bars by the same 3.469e-18 |
| `fillna=-1.0` | fills exactly the 20 warm-up bars |

The hole case is the one place this column is less clean than an
integer-counting one: `rolling.mean`'s accumulation restarts after the gap,
so two bars past the hole differ in their last bits. That is measured and
pinned (`test_a_bad_close_empties_its_own_windows_and_leaves_a_tiny_residue`)
rather than written up as "nothing else moves", which would be false.

**Parameter guards** (400-bar frame, so 380 fired bars at the defaults):

| input | effective column | fires |
|---|---|---|
| `length` = None / 0 / −5 / 1 / 0.5 / 1.9 | `LEAN_TDD_20` | 380 |
| `length` = 2 / 2.9 (2 is the smallest accepted) | `LEAN_TDD_2` | 398 |
| `length` = 50 | `LEAN_TDD_50` | 350 |
| `length` = 399 | `LEAN_TDD_399` | 1 |
| `length` = 400 | returns `None` | — |

`length` below 2 falls back to 20 because a one-return window is just that
return's own magnitude when it is negative — the one-bar down-move, a
different feature. The rule is `int()` truncation, so a fraction is accepted
when it truncates to 2 or more (`2.9` is `LEAN_TDD_2`, not the default) and
falls back when it truncates below (`1.9` is `LEAN_TDD_20`); `length=50.9`
and `length=50` are the same column, and `length=10` against `length=60` is a
different column (Spearman 0.325681 on a 1,500-bar walk).

## Wiring

Five touch points, all five taken:

1. `pandas_ta/statistics/lean_tdd_20.py` — the indicator
2. `pandas_ta/statistics/__init__.py` — the export
3. `pandas_ta/__init__.py` → `Category["statistics"]` — discovery /
   `df.ta.strategy()`
4. `pandas_ta/core.py` → `df.ta.lean_tdd_20()` — the accessor
5. `tests/test_lean_tdd_20.py` — 109 tests

Counts that moved with it: `Category` 320 → 321, `df.ta.<name>()` 328 → 329
(README and `docs/IndicatorDictionary.md`, both generated/asserted),
`CATEGORY_TOTAL` in `tests/test_altport2_ports.py` 320 → 321, the
`statistics` bucket 29 → 30, the `docs/MLCompanionContract.md` tally
665 → 666 tagged columns / 308 → 309 `SF`, and the dictionary's probe header
322 → 323.

## Why statistics and not volatility

It is a dispersion statistic of the return distribution, taken against a
fixed target rather than against the window's own mean, which puts it next to
`stdev`, `variance`, `skew` and `kurtosis` — and next to `lean_hurst_100`
and `lot_zeroret_60`, the two other return-distribution screen ports, both
`statistics`. The counter-argument is real and is recorded rather than
waved away: the column's nearest shipped neighbour is `ui`, a `volatility`
member, at 0.6798 on one synthetic frame and 0.8123 on the screen's real
data. The category changes nothing about the column's values — it changes
which `df.ta.strategy(category=...)` run emits it.
