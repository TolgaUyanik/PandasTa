# `lean_momersion_20` — measured

Issue #86 (LEAN-MOMERSION-20), ported 2026-11-11 on branch
`issue-86-lean-momersion-20`. Column: **`LEAN_MOMERSION_20`**,
`pandas_ta/momentum/lean_momersion_20.py`.
**Status: SHIPPED. Gates A–F through.** Gate E ran on the committed port
(issue-solver, 2026-11-11, run `is86-lean_momersion_20-2b74e32d`): max
\|ρ\| **0.2560** vs `chop` over n = 396,828, per-frame max median 0.2528 over
89 frames, 0 frames at \|ρ\| ≥ 0.90 → **SHIP**, under the 0.76 ship line.
Nothing was struck; the column ships as wired. The row is recorded in
`docs/gate_e_ledger.csv`.

Every number here is printed by `python docs/measure_lean_momersion_20.py`
(pandas 2.3.3 / numpy 1.26.4), by
`python -m pytest tests/test_lean_momersion_20.py -q`, or — the Gate E
section and Gate C's real-data counts — by the launcher's Gate E run
(`gate_e_overlap.py`, outputs `is86-lean_momersion_20-2b74e32d`). Nothing in
this file was typed from expectation; where a number is *not* measured, the
line says so.

## What it is

    r[t]     = close[t] / close[t-1] - 1
    pair[t]  = sign(r[t]) * sign(r[t-1])        # +1 same, -1 opposite, 0 flat
    MC[t]    = count of pair > 0 over the trailing 20 pairs
    MRC[t]   = count of pair < 0 over the same window
    column   = 100 * MC / (MC + MRC)            # NaN when MC + MRC == 0

How much of the recent past was momentum rather than mean reversion. 100 is
pure continuation, 0 pure alternation, 50 the coin-flip line. A pair in which
either return is exactly zero has no sign to agree or disagree with and is
counted in neither, which is why the denominator is `MC + MRC` and not 20.

The window holds 20 PAIRS, so the column reads 22 closes and the warm-up is
21 bars.

## Source, and what "Apache-2.0 Lean" does and does not mean here

The issue names QuantConnect Lean's `MomersionIndicator` (Apache-2.0) and
states the formula:

> `MomersionIndicator(20): 100*MC/(MC+MRC), MC/MRC = same/opposite-sign consecutive return pairs`

⚠ **Lean's C# source is not in this worktree and web access is unavailable.**
It was not read in this session. So the attribution is an attribution, not an
oracle: Gate A below is against the issue's stated line, and anything Lean
does that the line does not say — what it emits before its window fills,
whether its period counts pairs or returns, which side a zero return falls
on — is **unverified here**. The prototype
(`docs/issues/screen/ind_screen.py`, candidate `lean_momersion_20`,
gitignored and local to the owner's machine) was read and is used as a second
implementation, not as the source.

## Gate A — correctness

**A1. Three hand-derived windows, exact integer arithmetic.** No
implementation was consulted to derive them; the module reproduces all three
exactly (`test_hand_derived_windows_are_exact`).

| closes | length | return signs → pairs | expected | module |
|---|---|---|---|---|
| `[100, 101, 102, 101, 103, 104, 103]` | 4 | `+ + - + + -` → `+ - - + -` | NaN×5, 50, 25 | identical |
| `[10, 11, 11, 12, 13, 12, 12, 13]` | 3 | `+ 0 + + - 0 +` → `0 0 + - 0 0` | NaN×4, 100, 50, 50, 0 | identical |
| `[10, 11, 11, 11, 11]` | 3 | `+ 0 0 0` → `0 0 0` | NaN×5 | identical |

The middle row is the one that matters: the zero pairs count neither way, so
the denominators are 1, 2, 2, 1 rather than 3, 3, 3, 3. The last row is the
`MC + MRC == 0` case — NaN, not 50 and not 0.

**A2. Against the screen prototype**, 1,500-bar walk, 1,479 fired bars:

| compared against | max \|diff\| | bit-equal | Spearman | NaN masks |
|---|---|---|---|---|
| the prototype retyped here | 7.105427e-15 | 1198/1479 | 1.000000 | equal |
| **the screen's own registry candidate, imported from `docs/issues/screen/ind_screen.py`** | 7.105427e-15 | 1198/1479 | 1.000000 | equal |

The imported row is the real candidate, not a retype: the measurement script
loads `REG["lean_momersion_20"]["fn"]` out of that file when the worktree has
it, and says so when it does not (a clone does not — `docs/issues/` is
gitignored).

The 7.1e-15 is one rounding and not a disagreement. The prototype spells the
value `100 * (MC / (MC + MRC))`; the module spells it `100 * MC / (MC + MRC)`,
the order the source formula is written in, which rounds once instead of
twice — so 1,198 of 1,479 bars are bit-equal and the other 281 differ in the
last bits. Ranks are untouched (Spearman 1.000000).

**A3. Against an independent per-window loop in plain Python scalars** (no
numpy, no pandas rolling, the counts written out), 400 bars / 379 fired:

| frame | max \|diff\| | bit-equal | NaN masks |
|---|---|---|---|
| walk | 0.000000e+00 | **379/379** | equal |
| the same walk (seed 5) rounded to 0.01 (0.50% zero returns) | 0.000000e+00 | **379/379** | equal |

**A4. Four readings the wording leaves open.** Each decided, and each priced
against the port on three frames rather than dismissed — a continuous walk
(seed 11, no exact price ties), a **second** walk (seed 55) rounded to 0.01
(0.27% zero returns), and that same seed-55 walk on a 0.5 grid (14.01%). The
grid rows are not the seed-11 walk re-rounded, so read down the column as
three frames rather than as one path at three resolutions:

| reading, and what this port does | frame | max \|diff\| | bit-equal | Spearman |
|---|---|---|---|---|
| a zero return counts NEITHER way. Rejected: `if (p > 0) MC++ else MRC++`, i.e. flat → mean reversion | walk | 0.000000e+00 | 1479/1479 | 1.000000 |
| | 0.01 grid | 5.555556e+00 | 1397/1479 | 0.997355 |
| | **0.5 grid** | **5.571429e+01** | 95/1479 | **0.839877** |
| the window holds `length` PAIRS. Rejected: `length` RETURNS, one pair fewer | walk | 4.473684e+00 | 0/1479 | 0.968501 |
| | 0.01 grid | 4.575163e+00 | 6/1479 | 0.971715 |
| | 0.5 grid | 1.190476e+01 | 374/1479 | 0.973052 |
| the warm-up is NaN. Rejected: emit the neutral 50 until the window fills | walk | — | 21 bars of a constant at the head; identical on all 1,479 fired bars | — |
| a window with no signed pair is NaN. Rejected: 50, or 0 | flat 300-bar frame | — | 0/300 fire | — |

Three things worth keeping from that table:

* **The zero-return reading is invisible on a continuous frame and decisive on
  a grid.** Bit-equal on the walk, Spearman 0.8399 on the 0.5 grid. Real
  quotes are a grid, so this is the reading that decides the column — and it
  is exactly the reading a straight transcription of `if/else` C# would get
  wrong.
* The returns-window reading is **not** only a different value: it fires one
  bar earlier (bar 20 against bar 21), because it reads one close less.
* The rejected 50-during-warm-up reading is not a value disagreement at all.
  It is a constant head, which this fork's ML contract reads as data.

**A5. The spellings that are NOT readings.** Only the SIGN of the return
reaches the counts, so these three are the same column, bit for bit, on all
three frames (`test_the_spellings_of_the_pair_agree_bit_for_bit`):

| spelling | max \|diff\| | bit-equal (each frame) |
|---|---|---|
| `log(close / close.shift(1))` instead of ratio − 1 | 0.000000e+00 | 1479/1479 |
| `close.diff()` — the raw price difference | 0.000000e+00 | 1479/1479 |
| `r * r.shift(1)` — the product of the RETURNS (the prototype's) | 0.000000e+00 | 1479/1479 |

The product spelling cannot differ through underflow either, and that is
arithmetic rather than luck: the smallest nonzero return float64 can carry
between two distinct closes is about eps = 2.220e-16, so the product of two
returns is bounded below by ~1e-32 — some 290 orders above the subnormal
floor. The two spellings can only disagree on exact zeros, where they agree
by construction.

## Gate B — causality, by mutant

The column is built from SIGNS and takes one of at most 21 values per window,
which breaks the usual probe: a sweep that replaces the future with a fresh
random path repeats the sign it replaced about half the time, and then the
counts do not move. So Gate B runs **two** probes. Both sweep **36 J values**
(J = 60..1460 step 40) on 1,500-bar frames and assert that nothing strictly
before J moves.

**B1. The path sweep** — replace every bar from J onward with a different
path:

| | walk | walk vs alternating | 0.01 grid | 0.5 grid |
|---|---|---|---|---|
| **real module** | **0/36** | **0/36** | **0/36** | **0/36** |
| mutant: column back-dated by `length` | 36/36 | 36/36 | 36/36 | 36/36 |
| mutant: `np.sign(r).shift(1)` → `.shift(-1)` | 19/36 | 19/36 | 12/36 | 11/36 |
| mutant: `px.shift(1)` → `px.shift(-1)` | 19/36 | 19/36 | 12/36 | 11/36 |
| mutant: `center=True` on the one rolling count | 36/36 | 36/36 | 35/36 | 36/36 |

The 19/36 and 11/36 cells are the PROBE, not a safe mutant: a one-bar-ahead
mutant can only move the single bar J − 1, and it does so only when the
replacement path's first return has the other sign.

**B2. The directed probe** — for each J, multiply every close from J onward
by 0.5 or 2.0, whichever **changes the sign of `r[J]`**: a reversal where
`r[J] != 0`, and flat → up where it is zero. A power of two divides out of
every later return bit-exactly, so exactly ONE return changes. Measured
premise, not assumed: the sign changes at 36/36 J on every frame, and no
other return moves at all
(`test_the_directed_probe_really_flips_exactly_one_return`).

| | walk | alternating | 0.01 grid | 0.5 grid |
|---|---|---|---|---|
| **real module** | **0/36** | **0/36** | **0/36** | **0/36** |
| mutant: column back-dated by `length` | **36/36** | **36/36** | **36/36** | 33/36 |
| mutant: `np.sign(r).shift(1)` → `.shift(-1)` | **36/36** | **36/36** | **36/36** | 27/36 |
| mutant: `px.shift(1)` → `px.shift(-1)` | **36/36** | **36/36** | **36/36** | 27/36 |
| mutant: `center=True` on the one rolling count | **36/36** | **36/36** | **36/36** | 33/36 |

Every mutant is live on every frame (its output differs from the real
module's before any sweep runs), so none of these 32 cells is a mutant that
did nothing. Mutants are `importlib`-read from the module source and `exec`'d
in memory.

The 0.5 grid is the one frame that still misses J values, and the reason is
known rather than mysterious: 14.01% of its returns are zero, so a flat bar
at J − 1 makes `pair[J-1]` zero whichever way `r[J]` points, the flip is
absorbed, and the mutant has nothing to show on that bar.

The module has exactly **one** `.rolling(` call — a closure used three times
— so there is one window whose causality needs pinning, not three.

`offset` is the caller-reachable look-ahead and is pinned, not assumed:
`offset=2` is exactly the default shifted two bars later, `offset=-2` exactly
two bars earlier. The sweeps cover the default `offset=0`, which is what
`Category` uses.

## Gate C — reachability

**Real data: measured, from the launcher's Gate E run** (89 frozen ALTPORT-1
BIST frames, 398,849 pooled bars, run `is86-lean_momersion_20-2b74e32d`,
2026-11-11). `LEAN_MOMERSION_20` is non-NaN on **396,969** of those 398,849
bars (99.53%) and non-zero on **396,329** (99.37%), so `0 < fires < n` holds
on real data too and the column is not a constant. 1,880 bars are empty, of
which 1,869 are accounted for by the 21-bar warm-up on each of the 89 frames
(89 × 21, arithmetic on the frame count, not a per-frame measurement); the
remaining 11 were not attributed to a cause in this session. The 640 exact
zeros are windows in which every signed pair alternated.

The rows below are **synthetic**.

1,500-bar paths, 1,479 fired bars each:

The four AR(1) rows share ONE set of innovations (seed 40), so the ordering
across them is the φ effect and not four unrelated draws. The walk rows are
their own paths: seed 11 continuous, seed 55 for the two grids.

| path | distinct | min | p10 | median | p90 | max | share > 50 |
|---|---|---|---|---|---|---|---|
| AR(1) returns, φ = +0.8 (persistent) | 11 | 50.0000 | 65.0000 | **80.0000** | 95.0000 | 100.0000 | 0.9980 |
| AR(1) returns, φ = +0.4 | 13 | 30.0000 | 50.0000 | **65.0000** | 75.0000 | 90.0000 | 0.8377 |
| gaussian walk, iid returns (seed 11) | 14 | 20.0000 | 35.0000 | **50.0000** | 60.0000 | 85.0000 | 0.4104 |
| AR(1) returns, φ = −0.4 | 15 | 5.0000 | 20.0000 | **35.0000** | 45.0000 | 75.0000 | 0.0210 |
| AR(1) returns, φ = −0.8 | 11 | 0.0000 | 5.0000 | **20.0000** | 35.0000 | 50.0000 | 0.0000 |
| hard alternating log returns | 1 | 0.0000 | 0.0000 | **0.0000** | 0.0000 | 0.0000 | 0.0000 |
| the seed-55 walk at 0.01 | 25 | 15.7895 | 35.0000 | **50.0000** | 60.0000 | 80.0000 | 0.3989 |
| that walk on a 0.5 grid | 87 | 11.1111 | 29.4118 | **50.0000** | 64.7647 | 100.0000 | 0.4239 |

`0 < 1479 < 1500` fired on every one of them, so Gate D's non-constant
requirement is met with room — except on the alternating path, which is a
genuine constant 0 and is the point of that row.

**The level is honest in the median, and the spread is the caveat.** For iid
returns the population value is exactly 50 (consecutive return signs are
independent, so a pair is same-sign with probability 1/2). Over **2,000
independent 20-pair iid-return windows**: mean 50.1300, median **50.0000**,
sd 11.2276, p10 35.0000, p90 65.0000, above 50 on 42.20%, finite on
2,000/2,000. So the column is unbiased in the median but ±15 points at the
deciles: one reading of 60 is not a regime.

**Not drift-invariant, and that is pinned on purpose.** Unlike most of this
fork's window statistics, drift moves this column — it makes up-moves
likelier, so it changes the signs. Walk vs the same walk at +0.004 of log
drift a bar: max \|diff\| **40.0000**, bit-equal on 527/1479, Spearman
**0.382917**, NaN masks equal. `test_it_is_not_drift_invariant_and_that_is_pinned_on_purpose`
fails if a future change makes it invariant, because that would be a
different column.

## Gate D — scale-free

1,500-bar frames, 1,479 fired bars each. Every rescale is **bit-identical**,
not merely close:

| rescale | walk (seed 11) | the seed-55 walk at 0.01 | that walk on a 0.5 grid |
|---|---|---|---|
| ×8 | **1479/1479** | **1479/1479** | **1479/1479** |
| ×64 | **1479/1479** | **1479/1479** | **1479/1479** |
| ×10 | **1479/1479** | **1479/1479** | **1479/1479** |
| ×3.7 | **1479/1479** | **1479/1479** | **1479/1479** |

NaN masks agree on all twelve, and max \|diff\| is 0.000000e+00 throughout.
×8 and ×64 are exact because `8a / 8b` is the same double as `a / b`. ×10 and
×3.7 are exact for a different reason, which is why this column behaves
better under a rescale than most of the fork's: only the SIGN of the ratio
reaches the counts, `fl(k·x)` is monotone so a rescale cannot reorder two
closes, and the quotient of two DISTINCT doubles never rounds to exactly 1.0
— for adjacent `a`, `b` the exact ratio is `1 + u/b` with `u/b` in
(2⁻⁵³, 2⁻⁵²], strictly past the midpoint between 1.0 and its neighbour — so
the division cannot destroy a sign either.

**Where that stops: FUSION, measured rather than asserted.** `fl(k·a)` and
`fl(k·b)` can be the SAME double for two distinct closes, and that turns a
signed pair flat. The arithmetic bound is weaker than it first looks: two
closes `g` ulps apart land `g·k·2^(e−f)` ulps apart in the product's binade
(`x` ∈ [2^e, 2^(e+1)), `k·x` ∈ [2^f, 2^(f+1))), and the two binade
constraints only give `k·2^(e−f)` ∈ (1/2, 2) — at k = 10 with `x` ∈ [0.8, 1),
where 10x lands in [8, 16), it is 10·2⁻⁴ = **0.625**, so one-ulp neighbours
come out 0.625 ulp apart and round together. The same k at `x` ∈ [0.5, 0.8)
gives 1.25, so fusion is binade-dependent rather than a property of k.

From there, **only closes exactly one ulp apart can ever fuse**, in two
steps rather than one:

* the widest fusion window is **1.5 ulp**, and it is at a power of two:
  around `d = 2^(f+1)` everything within half the spacing below (0.5 ulp of
  the lower binade) and half the spacing above (1 ulp of it) rounds to `d`.
  Since the factor stays above 1/2, the scaled gap is more than `g/2` ulps,
  so `g >= 3` cannot fuse;
* `g = 2` needs the step past that. Fusing at `d = 2^(f+1)` requires the
  lower product `k·x >= d·(1 − 2⁻⁵⁴)`, which pushes the factor above
  `1 − 2⁻⁵⁴`, and then two ulps of separation land more than `2 − 2⁻⁵³` ulps
  apart — outside even the 1.5-ulp window. Inside a binade the window is
  1 ulp and `g = 2` is already more than one ulp.

Which leaves `g = 1`, and that is exactly what the measurement below shows.

Measured on a 300-bar frame of adjacent doubles straddling 1.0 — every move
exactly one ulp, 279 fired bars, and **0.0000 of its returns read as zero at
scale 1**, which is the ratio claim above holding:

| rescale | adjacent pairs fused | zero returns after scaling | NaN masks | bit-identical | max \|diff\| |
|---|---|---|---|---|---|
| ×8 | **0** / 299 | 0.0000 | equal | **279/279** | 0.000000e+00 |
| ×64 | **0** / 299 | 0.0000 | equal | **279/279** | 0.000000e+00 |
| ×10 | 58 / 299 | 0.1940 | equal | 141/279 | 6.000000e+01 |
| ×3.7 | 10 / 299 | 0.0334 | equal | 224/279 | 1.653846e+01 |

So the Gate D claim is bounded, and the bound is fusion: ×8/×64 are
bit-identical on any frame of normal doubles whose `k·close` does not
overflow (the arithmetic is exact, 0 pairs fused — the two holes in an
unqualified "unconditionally" are a close that is subnormal unscaled and
normal scaled, which the module's guard treats as missing before the rescale
and not after, and `k·close` overflowing near 1e308), and ×10/×3.7 are
bit-identical under those same two conditions plus consecutive closes at
least 2 ulps apart. No real frame comes near the 1-ulp case — one tick over
the price is 1e-9 even at a price of 1e6 with a 0.001 tick, seven orders
above the 2.2e-16 relative size of an ulp — but that last step is an
argument from tick size, not a measurement: **no real frame was rescaled**.
Gate E's run is where real data was read, and it measures overlap, not
rescale invariance.
`test_the_scale_free_claim_stops_at_one_ulp_moves` pins the bound, the fused
counts and the zero-return shares, so none of it can be quietly widened.

`0 < fires < n`: 0 < 1,479 < 1,500 on each frame.

**Why the distinct-value counts are small, and why that is not a constant
column.** `100 * MC / (MC + MRC)` with `MC + MRC <= 20` has **129** reachable
values. But on a frame with no exact ties every pair is signed, so the
denominator is always 20 and the value is a multiple of 5: 14 distinct values
on the seed-11 walk (all multiples of 5, measured), against 25 on the seed-55
walk at 0.01 and 87 on that walk at 0.5, where flat bars shrink the
denominator. Those last two are one path at two resolutions; the 14 is a
different path, so read 14 vs 25 as "continuous vs gridded" and not as one
frame re-rounded. The column is discrete by construction;
`docs/IndicatorDictionary.md` tags it `SF`.

## Gate E — attribution

**Measured on the port. Verdict SHIP — nothing struck.** Run by issue-solver
after the porting session, 2026-11-11, run id
`is86-lean_momersion_20-2b74e32d`, recorded in `docs/gate_e_ledger.csv`.

| column | max \|ρ\| | against | set | n | per-frame max median \|ρ\| | frames | frames \|ρ\| ≥ 0.90 | verdict |
|---|---|---|---|---|---|---|---|---|
| `LEAN_MOMERSION_20` | **0.2560** | `chop` | compute_all | 396,828 | **0.2528** (`chop`) | 89 | **0** | **SHIP** |

The signed pooled ρ is **−0.2560**: more momentum, less chop. Both the pooled
and the per-frame figure are far under the 0.76 ship line, so the band is
SHIP on either leg and not a near miss — `r3-perframe-0.90` bands, `CLAUDE.md`
Gate E row.

Run facts, from the run's `meta.json` and `overlap_max.csv`: default
parameters (`kwargs {}`), 89 frames, 398,849 pooled bars, 687 comparators
(329 `compute_all` + 358 `ml_features` manifest `1d`), 1 of them degenerate,
canary `AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS bit-equal`, data stamp
`1be6495e`, pandas 2.3.3 / numpy 1.26.4. Module sha1
`3e252cb5ac6ce460319578ad9ac78a42dd0d6cea`, tree sha1
`0e927f3aa6713d2a100c263c296b3b91c5d6352e`.

Top comparators measured on the port:

| \|ρ\| | against | set | n |
|---|---|---|---|
| 0.2560 | `chop` | compute_all | 396,828 |
| 0.2520 | `BB_BWidth` | compute_all | 396,969 |
| 0.2310 | `CHOP` | compute_all | 396,300 |
| 0.2251 | `Swing_Range_pct` | manifest | 396,969 |
| 0.2243 | `BB_BWidth_Pctl` | manifest | 391,896 |

The three leaders are volatility/choppiness measures, not momentum ones, and
the manifest's best (0.2251) is under the compute_all best — so no shipped
column restates this one on either side of the comparator set.

**Against the prototype the issue screened** (2026-10-24, run
`screen_20261024`; the owner's numbers, not this session's): max \|ρ\|
0.2560 vs `chop` over n = 396,828, top-5 per-frame max median 0.2528 → SHIP,
next comparators `BB_BWidth` 0.2520 and `CHOP` 0.2310. The port reproduces
all five of those figures to the four decimals the issue states them in,
including the comparator ordering — so the port is the column the screen
measured, not a near relative of it. The stage-2 fork overlap (0.2584 vs
`chop:CHOP_14_1_100` over 12 frames) is not Gate E and was not re-measured.

**Nearest neighbours on one 1,500-bar synthetic walk — NOT Gate E** (12
shipped columns plus one hand-rolled probe, one frame; Gate E is 687
comparators over 89 frozen BIST frames):

| \|ρ\| | column |
|---|---|
| 0.6320 | lag-1 autocorrelation of the last 20 log returns (hand-rolled, not shipped) |
| 0.3042 | `vhf_28` |
| 0.2989 | `chop_14` |
| 0.1973 | `skew_30` |
| 0.1904 | `er_10` |
| 0.1310 | `natr_14` |
| 0.0935 | `lean_hurst_100` |
| 0.0475 | `kurtosis_30` |
| 0.0197 | `psl_12` |
| 0.0104 | `cfo_9` |
| 0.0091 | `entropy_20` |
| 0.0062 | `rsi_14` |
| 0.0012 | `zscore_30` |

Two readings worth keeping. The hand-rolled lag-1 return autocorrelation
leads at 0.6320, which is the smell test working: that is the same question
asked continuously instead of by counting signs, and it is **not** a shipped
column, so it is not a Gate E comparator. Among shipped columns `chop` leads
on this frame too, which matches what the issue's prototype screen found on
real data (0.2560 pooled). And `psl_12` — the share of UP bars, the nearest
relative by construction — comes in at 0.0197: counting same-sign pairs is
not counting up bars.

## Gate F — suites

Run in this worktree:

At the port (before the Gate E row was recorded):

* `python -m pytest tests/test_lean_momersion_20.py -q` → **104 passed** in
  3.91 s.
* `python -m pytest -q` → **3 failed, 5562 passed, 83 skipped** in 116.10 s.
  The three failures were the two `CLAUDE.md` "Known breaks"
  (`test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`,
  which needs the sibling `../AlternativeRepos` checkout and is deselected in
  CI, and `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`,
  the `supertrend` citation into the untracked `docs/pine/`) plus
  `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
  which reported `['lean_momersion_20', 'mtd_ret']`: the Gate E row this port
  owed, and one owed before it.

At this receipt session, with the Gate E row recorded:

* `python -m pytest tests/test_lean_momersion_20.py -q` → **104 passed** in
  3.84 s.
* `python -m pytest -q` → **3 failed, 5569 passed, 83 skipped** in 118.04 s.
  Same three names. Seven more tests pass than at the port; the suite grew by
  the ledger's per-row parametrisations, which were not counted separately.
  `test_every_indicator_that_needs_a_row_has_one` now reports
  `['mtd_ret']` only — `lean_momersion_20` is off that list, and the one
  remaining name was owed before this port and is not ours. CI into `dev`
  skips it under `GATE_E_PENDING_OK=1`.

The launcher runs both repos' suites in clean worktrees.

## Edge cases, measured

| case | behaviour |
|---|---|
| 21 bars | returns `None` (`verify_series` floor: 20 pairs need 22 closes) |
| exactly 22 bars | fires 1/22, at bar 21 |
| exactly flat 300-bar frame | 0/300 fire — every pair is flat, so `MC + MRC == 0` |
| staircase, one step up every 10 bars | 0/300 fire; 0 of 298 known pairs are signed, because the steps are never adjacent |
| one-tick alternation 100.00 / 100.01 | fires 279/300, every value 0.0 |
| one NaN close at bar 200 | empties exactly 22 bars, 200..221; **0** other bars move, on either side |
| one zero / negative / infinite / subnormal (1e-310) close | each empties exactly the same 22 bars, and moves nothing else |
| `fillna=-1.0` | fills exactly the 21 warm-up bars |

The hole case is cleaner than it is for this fork's float aggregations: the
counts are integers, so there is no online-accumulation drift after the hole
— nothing outside bars 200..221 moves at all.

**Parameter guards** (400-bar frame, so 379 fired bars at the defaults):

| input | effective column | fires |
|---|---|---|
| `length` = None / 0 / −5 / 1 / 0.5 / 1.9 | `LEAN_MOMERSION_20` | 379 |
| `length` = 2 / 2.9 (2 is the smallest accepted) | `LEAN_MOMERSION_2` | 397 |
| `length` = 50 | `LEAN_MOMERSION_50` | 349 |
| `length` = 398 | `LEAN_MOMERSION_398` | 1 |
| `length` = 399 | returns `None` | — |

`length` below 2 falls back to 20 because a one-pair window can only read 0
or 100 — a flag, not a share. The rule is `int()` truncation, so a fraction
is accepted when it truncates to 2 or more (`2.9` is `LEAN_MOMERSION_2`, not
the default) and falls back when it truncates below (`1.9` is
`LEAN_MOMERSION_20`); `length=50.9` and `length=50` are the same column, and
`length=10` against `length=60` is a different column (Spearman < 0.9 on a
1,500-bar walk).

## Wiring

Five touch points, all five taken:

1. `pandas_ta/momentum/lean_momersion_20.py` — the indicator
2. `pandas_ta/momentum/__init__.py` — the export
3. `pandas_ta/__init__.py` → `Category["momentum"]` — discovery /
   `df.ta.strategy()`
4. `pandas_ta/core.py` → `df.ta.lean_momersion_20()` — the accessor
5. `tests/test_lean_momersion_20.py` — 104 tests

Counts that moved with it: `Category` 319 → 320, `df.ta.<name>()` 327 → 328
(README and `docs/IndicatorDictionary.md`, both generated/asserted),
`CATEGORY_TOTAL` in `tests/test_altport2_ports.py` 319 → 320, and the
`docs/MLCompanionContract.md` tally 664 → 665 tagged columns / 307 → 308
`SF`.

## Why momentum and not statistics

It is a count of same-sign consecutive returns, which is what `psl` (the
share of up bars, `momentum`) already is a cousin of. The shipped column
nearest by construction is `psl`, and the measured correlation on a synthetic
walk is 0.0197 — related in kind, unrelated in value.
