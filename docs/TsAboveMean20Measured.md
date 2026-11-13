# TS-ABOVE-MEAN-20 — `ts_above_mean_20`, measured

Issue #97 (PandasTa), parent #31 ALPHASETS, screen of 2026-10-24.
Ported 2026-11-13 on branch `issue-97-ts-above-mean-20`.

```
TS_ABOVE_MEAN_20 = (how many of a 20-return window's simple returns are
                    STRICTLY above that window's own mean) / 20
```

Source: tsfresh `feature_calculators` (MIT), `count_above_mean`, as issue #97
states it — `count_above_mean / n on 20 returns`.

Every number below comes from `docs/measure_ts_above_mean_20.py` unless the
line says otherwise; the section names (`gate_a`, `gate_b`, …) are that
script's arguments. The tests that hold the same facts are in
`tests/test_ts_above_mean_20.py` (166 of them), except the Gate E and
real-data Gate C numbers, which come from the launcher's run (§9) and are
pinned out of `docs/gate_e_ledger.csv`.

**Gate E: MEASURED, 2026-11-13, run `is97-ts_above_mean_20-5d78f565` —
`TS_ABOVE_MEAN_20` is SHIP**, pooled max |ρ| **0.35937568662749647** vs
`PVT_Slope_norm` at n = 396,970, per-frame max median
**0.3580864882804631** against the same comparator over 89 frames. §9 has
the run and all of its numbers; the row is in `docs/gate_e_ledger.csv`.
Nothing is struck, so nothing is removed.

---

## 0. What the column is, in one paragraph

It is a **backwards skewness reading on a 20-return window**. A few large
gains pull the window mean up, so fewer returns clear it and the column goes
DOWN. The COUNT is invariant to any affine map of the returns with a positive
slope, so it is neither a volatility nor a direction column (the reported
NaN MASK is not — §4, G6); it is coarse (19 reachable values) and heavily
tied; and its range is `[1/20, 19/20]` and not `[0, 1]`, because a count of 0
or 20 requires all twenty returns to be equal.

## 1. Gate A — correctness against the source formula

**The oracle is the issue's line plus the published definition of
`feature_calculators.count_above_mean` (`np.where(x > np.mean(x))[0].size`).
tsfresh is NOT installed in this worktree and web access is unavailable**, so
nothing here is a read of tsfresh's own code;
`test_tsfresh_is_not_installed_here` records that so the claim cannot rot into
"checked against tsfresh". Anything tsfresh does that those two sources do not
state — how it treats NaNs — is unverified here. The 20 is the issue's own
parameter.

This column is a COUNT, so every check below is **bit-equality**, not a
tolerance.

### A1 — against the source applied window by window

A Python loop handing each window to a retype of `count_above_mean`; shares no
code with the module (no `sliding_window_view`, no pandas rolling).

| frame (1,500 bars) | masks | bit-equal | Spearman |
|---|---|---|---|
| walk | identical | 1480/1480 | 1.000000 |
| tick-rounded | identical | 1480/1480 | 1.000000 |
| AR(1) φ=+0.5 | identical | 1480/1480 | 1.000000 |
| AR(1) φ=−0.5 | identical | 1480/1480 | 1.000000 |
| heavy-tailed t(2) | identical | 1480/1480 | 1.000000 |
| right-skewed | identical | 1480/1480 | 1.000000 |
| left-skewed | identical | 1480/1480 | 1.000000 |
| two-point | identical | 1480/1480 | 1.000000 |
| trending | identical | 1480/1480 | 1.000000 |

### A2 — against a `math.fsum` scalar loop

The window mean taken by `math.fsum`, exact up to one final rounding, in plain
Python. Bit-equal **1480/1480** with identical masks on the walk, the
heavy-tailed frame and the right-skewed frame.

### A3 — against an EXACT rational oracle

Every float return is a rational, so the window mean is a rational and every
comparison can be decided with no rounding at all (`fractions.Fraction`). This
is the only check that can see the one thing float can do to this column:
decide a comparison the wrong way.

| frame | masks | exact on | max \|diff\| |
|---|---|---|---|
| walk | identical | 1480/1480 | 0.000e+00 |
| tick-rounded | identical | 1480/1480 | 0.000e+00 |
| two-point | identical | 1480/1480 | 0.000e+00 |
| right-skewed | identical | 1480/1480 | 0.000e+00 |
| mean-dominated, `\|mean\|/sd` = 1e5 | identical | 580/580 | 0.000e+00 |

**The float mean has not flipped a single comparison in any run here**, the
mean-dominated path included — which is where the window sum's cancellation is
worst and where the sibling ports (`ts_cid_ce_20`, `ts_aggac_60`) lose 1e-9.
This column loses nothing there because it reads only the ORDER of the sum
against its own terms, and D6 below measures how much room that order has.

### A4 — the reachable range is [1/20, 19/20], not [0, 1]

Derived first: if no return were above the mean, all would be at or below it,
and `sum = length * mean` then forces every one of them EQUAL — and
symmetrically for all-above. So any window whose returns are not all identical
has between 1 and `length − 1` of them above the mean. A window of identical
returns is refused by the floor (§4), so **the column cannot read 0.0 or 1.0
at all**.

Counted over 13,320 fired bars of the nine frames: min **0.05**, max
**0.95**. Per frame:

| frame | min | max | distinct of 19 |
|---|---|---|---|
| walk | 0.25 | 0.70 | 10 |
| tick-rounded | 0.30 | 0.70 | 9 |
| AR(1) φ=+0.5 | 0.30 | 0.70 | 9 |
| AR(1) φ=−0.5 | 0.30 | 0.65 | 8 |
| heavy-tailed | 0.05 | 0.95 | **19** |
| right-skewed | 0.20 | 0.55 | 8 |
| left-skewed | 0.45 | 0.80 | 8 |
| two-point | 0.20 | 0.85 | 14 |
| trending | 0.30 | 0.75 | 10 |

Both ends are attained by a hand-built window too: nineteen equal gains after
one zero reads 0.95, one gain among nineteen zeros reads 0.05.

### A5 — four readings the one-line formula leaves open, priced

On the 1,500-bar walk, against the shipped column:

| reading | Spearman | bit-equal (shared bars) | max \|diff\| |
|---|---|---|---|
| log returns instead of simple | 0.983938 | 1395/1480 | 0.1000 |
| 20 CLOSES, i.e. 19 returns | 0.888618 | 0/1480 | 0.2237 |
| of the 20 CLOSES, not of the returns | 0.091872 | 262/1480 | 0.3500 |
| `>=` instead of `>` | 1.000000 | 1480/1480 | 0.0000 |
| the raw COUNT instead of the share | 1.000000 | 0/1480 | 13.3 |

* **Simple returns** (`close/close.shift(1) - 1`), which is the prototype's
  `ret`. Log returns are a close but different column.
* **20 RETURNS, so 21 closes**, first value at bar 20. The 19-return reading
  is the off-by-one a reader makes; it is priced so it is not re-argued. The
  statistic of the CLOSES rather than of the returns is a different question
  entirely (0.0919).
* **Strict `>`**, the source's. This is the one choice no frame here can see:
  a tie with a 20-way AVERAGE does not happen by accident, and there are **0
  exact ties in 29,600 window/return pairs** of each of the walk, the
  tick-rounded frame and the two-point frame. So it is pinned by a constructed
  window instead — closes `[100, 50, 50, 75]` have returns
  `[-0.5, 0.0, +0.5]`, which sum to exactly 0.0, so at `length` 3 the strict
  form reads 1/3 and `>=` reads 2/3.
* **The SHARE**, the issue's `count_above_mean / n`. Dividing by `length` is
  an exact rescaling (Spearman 1.000000), so it is the one choice a rank miner
  cannot see.

### A6 — hand-derived windows

| window of 20 returns | reads | expected |
|---|---|---|
| alternating ±1% | 0.500000 | 10/20 |
| one +50% among nineteen zeros | 0.050000 | 1/20 |
| one −50% among nineteen zeros | 0.950000 | 19/20 |
| ramp 0.1% … 2.0% | 0.500000 | 10/20 |
| twenty identical returns | NaN | refused (§4) |

### A7 — against the screen prototype: it IS the same column

The prototype (`docs/issues/screen/ind_screen.py`, candidate
`ts_above_mean_20`, local to the owner's machine) is
`roll(ret(c), 20, w_count_above_mean)` with
`w_count_above_mean(W) = (W > W.mean(1, keepdims=True)).mean(1)`: the same
windows, the same mean, the same strict comparison, and `_from_win` writing at
`out[n-1:]`.

**Bit-equal on 1,480 of 1,480 shared fired bars of each of the nine frames,
Spearman 1.000000.** The NaN masks differ in exactly two ways, both in this
port's favour:

1. the prototype's first fired bar is **19**, not 20, and it reads **0.00**
   there — its window holds the undefined first return, whose NaN mean makes
   every comparison False. That is the arithmetically impossible value of §A4,
   emitted on every frame;
2. a non-finite close empties this port's windows and not the prototype's: one
   NaN at bar 200 of a 1,500-bar walk leaves **22** bars where one is NaN and
   the other is not (the 21 windows holding the bad close, plus bar 19), with
   **1,459 of 1,459** bit-equal elsewhere.

Because Gate E's statistic is a Spearman over the bars where both fire, the
screen's figures (max |ρ| 0.3594 vs `PVT_Slope_norm`, n = 396,970, per-frame
max median 0.3581 → SHIP) were expected to carry over. **They were not a
receipt** — and §9 now reports the run that is: the port measures
0.35937568662749647 against the same comparator at the same n, agreeing with
the screen to the four decimals the screen published.

## 2. Gate B — causality, by mutant

Six mutants, each `importlib`-read from the shipped source, mutated by one
line and `exec`'d in memory. Three mechanisms: the write index back-dated, a
read index moved into the future, and the floor's own index (the sixth, below,
which needs a designed frame).

| mutant | what it breaks |
|---|---|
| `back_date_two` | `out[length-1:]` → `out[length-3:n-2]`: every value lands 2 bars early |
| `back_date_full` | `out[length-1:]` → `out[:rows]`: the whole column lands `length-1` bars early |
| `forward_window` | the windows are taken from `np.roll(r, -1)`: each reads one return ahead |
| `forward_return` | `px/px.shift(1)` → `px.shift(-1)/px`: bar T's return reads close T+1 |
| `future_mean` | the comparisons are made against the NEXT window's mean |
| `shifted_floor` | `hi`/`lo` rolled by one window: bar T's NaN mask reads window T+1 |

The sweep replaces every close from bar J on with another frame's and asks
whether any bar BEFORE J moved — 37 offsets, 40 … 1480.

**The real module leaks 0 of 37 on each of three frames** (walk, tick-rounded,
heavy-tailed) **and at `length` 5, 60 and 250 on the walk.**

The first five are LIVE (each changes the column) and caught by the blind
sweep:

| mutant | walk | tick-rounded | heavy-tailed |
|---|---|---|---|
| `back_date_full` | 37/37 | 37/37 | 37/37 |
| `back_date_two` | 37/37 | 34/37 | 37/37 |
| `future_mean` | 37/37 | 33/37 | 37/37 |
| `forward_return` | 37/37 | 32/37 | 36/37 |
| `forward_window` | 37/37 | 32/37 | 36/37 |

The cells below 37 are the sweep's own bluntness and not a leak the mutant
hides: a perturbation that changes no COUNT is invisible to it, and a
tick-rounded frame's returns are coarse enough that a replaced tail sometimes
leaves the prefix counts alone. The tests band these (floors of 20–30) rather
than pinning them, because CI's runner has measured different last bits for the
same seeds (commit 22fe27b).

### The sixth mutant: the floor's own index, where the blind sweep fails

`hi, lo = windows.max(axis=1), windows.min(axis=1)` → both rolled by one
window, so bar T's NaN mask would read window T+1. A real look-ahead, in the
one index the five mutants above do not touch.

It is **LIVE on every frame**, and it moves exactly **two** bars — the set,
not a count, so neither can be quietly dropped:

| frame | bars moved | bar 19 | last bar | blind sweep |
|---|---|---|---|---|
| walk | `[19, 1499]` | NaN → **0.0** | 0.55 → NaN | **0/37** |
| tick-rounded | `[19, 1499]` | NaN → **0.0** | 0.55 → NaN | **0/37** |
| heavy-tailed | `[19, 1499]` | NaN → **0.0** | 0.70 → NaN | **0/37** |

* **Bar 19 is the look-ahead.** `reported` is False at exactly one index —
  the window holding the undefined first return — so the mutant reads window
  1's extrema there and emits 0.0, the arithmetically impossible value of
  §A4.
* **The last bar is a `np.roll` WRAP, not a look-ahead.** The rolled extrema
  of window 0, which are NaN, land on the last window, so a reported value
  becomes NaN. Worth naming because it is the other half of "two bars", and
  because a reader who assumed one would wonder where it came from.

**0 of 37 is not a clean module; it is a blind test**, and for two separate
reasons: bar 19 precedes every offset of the sweep (those start at 40) and
reads 0.0 in the perturbed run too, while the last bar follows every offset
and `_caught` only inspects bars BEFORE one. So the gate is closed by a
DESIGNED frame instead: a walk interrupted every 40 bars by 25 bars of
exactly-zero returns — 36 patches, each supporting `25 − 20 + 1` = 6 all-zero
windows, so **216 interior** windows are emptied, plus the 20 warm-up bars =
236 NaN of 1,500, 1,264 fired. There the real module still leaks **0 of 37**
and the mutant is caught **36 of 37**.

Pinned by `test_the_floor_index_mutant_is_live_but_invisible_to_the_blind_sweep`
and `test_the_designed_probe_catches_the_floor_index_mutant`.

## 3. Gates C and D

### C — reachability

Every one of the nine synthetic frames: fires **1480 of 1500**, every fired
bar non-zero, at least 8 distinct values. A flat 300-bar frame and a
constant-return ladder fire on **0** bars, which is §4.

**Gate C on real data is MEASURED**, out of the launcher's Gate E run
(`is97-ts_above_mean_20-5d78f565`, §9): over the 89 BIST frames
`TS_ABOVE_MEAN_20` is non-NaN on **397,069 of 398,849** pooled bars, and
**397,069** of those are non-zero — every bar it reports on.

Two things follow, and both are the arithmetic of those three numbers rather
than a reading of them:

* **398,849 − 397,069 = 1,780 = 20 × 89, exactly the warm-up.** So on the 89
  frames NONE of this port's guards emptied a window: not the relative floor
  of §4, not the per-return magnitude bound, not the bad-close rule — any
  window they emptied would be a NaN bar beyond bar 19 of its frame. The
  synthetic tables could only show those guards cost 1 bar (bar 19) and 0 body
  bars on nine clean frames; this shows 0 body bars on 398,849 real ones. It
  does NOT say the guards are idle in general: §4 measures each one firing on
  a frame built to make it fire.
* **No fired bar is exactly 0.0**, which is §A4's bound seen on real data:
  0.0 needs all twenty returns equal, and such a window is refused by the
  floor rather than reported as 0.0. The prototype of §A7 DOES emit 0.00, at
  bar 19 of every frame.

The pooled finite share is 397,069 / 398,849 = **0.99554**. The screen's
pre-flight below reports a WORST-FRAME share, a different statistic, so the
two are not comparable; it is kept as the corroboration it now is —
`docs/issues/screen/sanity.csv` line 72 (gitignored owner tracker, same
caveats as §5 — measured on the PROTOTYPE, and §A7 is the bridge):

```
ts_above_mean_20,0.9774346793349169,11,0.0,0.0,0.0
```

— worst-frame finite share **0.9774**, worst-frame distinct values **11**,
and prefix-causality, price ×8 and volume ×8 max relative differences all
exactly **0.0**. The 11 distinct values on a real frame sit beside the 10 on
the synthetic walk (§6), which is the coarseness claim corroborated on real
data rather than only on generated frames.

### D1 and D4 — ×8 and ×64 are bit-identical

`8a / 8b` is the same double as `a / b`, so a power-of-two rescale leaves the
returns bit-identical and everything downstream with them: **1480 of 1480**
fired bars on each of the nine frames, masks identical. At other lengths on
the walk (the script's D4): 1497/1497, 1495/1495, 1440/1440 and 1250/1250 at
`length` 3 / 5 / 60 / 250.

### D2 — ×10, ×3.7, ×0.1 and ×1.0000001 agree too, though they need not

These DO perturb the returns' last bits. They were measured bit-equal anyway
— **1480/1480 on every one of the nine frames**, and 0 of 199,980 bars moved
on a 200,000-bar walk — because a COUNT moves only when a perturbation
reorders a return and its own window mean.

### D3 — `0 < fires < n`, and not constant

1480 of 1500 on each frame, with 8 … 19 distinct values. At `length` 3 the
column takes exactly the two values 1/3 and 2/3, which is why `MIN_LENGTH` is
3 (at 2 it is identically 1/2).

### D5 — stronger than a price scale: an affine map of the RETURNS

The COUNT cannot change under `r → a·r + c` with `a > 0`: the mean maps the
same way, so the set of returns above it is the same set. Rebuilding the frame
from `r × 2`, `r × 0.5` and `r + 0.004` leaves the column **bit-equal on
1480/1480** with identical masks (banded in the test at `FIRED − 5`, because
the frames are rebuilt by `cumprod` and the returns that come back out differ
in their last bits; the band has not been used here). This is the property
that makes it neither a volatility nor a direction column.

⚠ **That invariance is the COUNT's, not the reported MASK's** — see §4, G6.
The floor is scale-invariant and not shift-invariant, so a drift CAN empty a
window the undrifted frame reports on.

### D6 — how much margin D2 has

A non-power-of-two rescale moves a return by about one ulp, i.e. ~2.2e-16 of
its own size. Over **199,980** windows of a 200,000-bar walk the smallest gap
`|r − mean| / max|r|` is **1.559e-07**. Nine orders of magnitude of margin —
a measurement, not a guarantee, and the reason the tests assert the margin
rather than a bit-equality they cannot promise.

### CPU kernels

`python docs/measure_ts_above_mean_20_cpu.py` sets
`NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` — the launcher's
exact list — before numpy is imported, asserts that those four really are
gone from the dispatch, and runs the module's tests in process: **165
passed**, numpy 1.26.4, same as without it.

⚠ That is those four features disabled, not "non-AVX kernels". The run on
this machine reports these still enabled: `SSSE3`, `SSE41`, `POPCNT`,
`SSE42`, `AVX`, `F16C`, `AVX512CD`, `AVX512_CLX`, `AVX512_CNL`, `AVX512_ICL`.
The script prints that list every run, so the claim cannot drift from what was
disabled.

## 4. The guards, each priced in both directions

### The floor is RELATIVE, and that is a departure from the sibling ports

`statistics/ts_c3_20.py`, `ts_binent_20.py` and `ts_cid_ce_20.py` floor a
return dispersion at an ABSOLUTE `4096 eps`. They divide by that dispersion;
this column does not divide by anything. What it needs protecting from is a
count decided by the rounding in the mean it compares against — and that error
scales with the window's own magnitude. So the floor is

```
reported  iff  (max r − min r) > 4096 * eps * max |r|
```

Both halves are measured:

| frame | relative floor (shipped) | absolute `4096 eps` |
|---|---|---|
| returns ≈ 1e-6, spread 1e-13 (honest) | fires **580/600** | fires **0/600** |
| returns ≈ 0.5, spread 1e-14 (rounding) | fires **0/600** | fires **0/600** |

On the first frame the shipped column is **exact on 580 of 580** bars against
the rational oracle, so an absolute floor would be throwing away a column that
is right.

The floor also carries the §A4 bound, in two steps:

* the exact mean is at most `hi − spread/length`, so with
  `spread > 4096·eps·amax` it clears `hi` by more than `4096/20` = **204.8
  ulps** of `amax`;
* the COMPUTED mean's error: naive summation of `length` terms is out by at
  most `(length−1)·eps·Σ|r| ≤ (length−1)·length·eps·amax`, so after dividing
  by `length` the mean is out by at most `(length−1)·eps·amax` = **19 ulps**,
  plus one more for the division itself.

About a 10× margin — and `1 ≤ count ≤ length − 1` was then COUNTED over every
window of every frame rather than left as a derivation.

### What the floor costs, and what it buys

Costs, on each of the nine clean frames: **1 bar — bar 19, the window holding
the undefined first return — and 0 body bars.**

Buys:

* a **flat** 300-bar frame: the unguarded spelling reports on all 280 body
  windows, every one of them **0.0**, a value this column cannot otherwise
  reach and which a tree would read as the calmest possible window rather than
  as missing data. The shipped column reports on none;
* a **1%-a-bar geometric ladder**, whose return is mathematically constant and
  differs only in its last bits in float64: the unguarded spelling reports 280
  body windows across **12 distinct values**, min 0.05, max 0.90, median 0.70
  — plausible-looking numbers out of nothing but rounding. The shipped column
  reports on none.

### The per-return magnitude bound

Every kept return has `|r| < max / (2 · length)` = **4.49e+306**, so a window's
sum cannot overflow and the mean cannot be an infinity whose comparisons all
read False (which would report a count of 0 — again the impossible value). The
same test drops a NaN and an infinite return, since a comparison against
either is False.

### A bad close empties exactly the windows holding it

A close that is NaN, infinite, zero, negative or subnormal has no usable
return, so it spoils TWO returns and empties the `length + 1` = 21 windows it
sits in. Measured on a 400-bar walk, with **0 earlier bars moved** in every
case:

| bad close at bar | further bars emptied |
|---|---|
| 0 | 1 |
| 1 | 2 |
| 19 | 20 |
| 200 | 21 |
| 398 | 2 |
| 399 | 1 |

`0.0`, `-100.0` and `1e-310` at bar 200 each empty 21, the same as a NaN.

### One enormous return stays LOCAL

This is where the module departs from the fork's `ts_ac1_60` and
`ts_cid_ce_20`, whose ONLINE pandas accumulators carry a residue forward and
whose receipts record a single 1e+8 return poisoning every later bar. Here
every window is reduced from its own `length` values by
`sliding_window_view`, so nothing crosses a window boundary.

Measured on a 2,000-bar frame priced at ~1e-198 — so that even the largest
jump leaves every close a normal float, and what engages at the top of the
sweep is this module's own bound and not an overflow of the price — with a
single return planted at bar 200 and 1,780 bars after it:

| planted return | the 20 windows holding it | bars 220 … |
|---|---|---|
| ×1e+02 | all **0.05** | bit-identical |
| ×1e+06 | all **0.05** | bit-identical |
| ×1e+08 | all **0.05** | bit-identical |
| ×1e+100 | all **0.05** | bit-identical |
| ×1e+300 | all **0.05** | bit-identical |
| ×1e+307 (above the bound) | all NaN | bit-identical |

0.05 is the RIGHT answer, not a degradation: one return above the mean, which
is what a window containing one enormous return has.

### The floor is scale-invariant but NOT shift-invariant (G6)

`hi − lo` is unchanged by `r → r + c` while `4096·eps·max|r|` grows with `c`,
so the affine invariance of §D5 belongs to the COUNT and not to the reported
MASK: a drift can empty a window the undrifted frame reports on. Measured on
returns of about 1e-6 whose window spread sits just under the threshold a
0.004 drift would impose:

| frame | fires | median window spread | median floor |
|---|---|---|---|
| no drift | **580/600** | 1.332e-15 | 9.095e-19 |
| +0.004 a bar | **0/600** | 1.332e-15 | 3.639e-15 |

The spread does not move; the floor does. Only a window that close to the
floor is affected — the nine frames of §D5 are nowhere near it, which is why
they come back bit-equal. Pinned by
`test_that_invariance_is_the_counts_and_not_the_reported_masks`.

### Short input and a bad `length`

20 closes at `length` 20 returns `None` (not a frame of NaNs); 21 closes fire
on exactly 1 bar. `length` of `None`, 0, 2 or −5 falls back to 20.

## 5. In-fork overlap — what Gate E's 687 comparators cannot see

Gate E compares against the parent repo's engine columns, which hold no
pandas_ta port. **This column is a coarse, rank-based reading of the window's
return SKEWNESS**, and this fork already ships a return-skewness column, so
the overlap is measured here.

Spearman against `OSAP_RETSKEW_21` (shipped, `Category["statistics"]`) and
against a rolling `skew(r, 20)` at the same window:

| frame | `skew(r,20)` | `OSAP_RETSKEW_21` | `TS_KURT_60` | `TS_AC1_60` | `TS_CID_CE_20` | `LEAN_MOMERSION_20` | `mean(r,20)` | `sd(r,20)` |
|---|---|---|---|---|---|---|---|---|
| walk | −0.6229 | −0.6141 | 0.0910 | 0.2181 | −0.0158 | −0.0981 | 0.0699 | −0.0746 |
| tick-rounded | −0.6211 | −0.6133 | 0.0863 | 0.2211 | −0.0176 | −0.0896 | 0.0694 | −0.0792 |
| AR(1) φ=+0.5 | −0.6283 | −0.6192 | 0.1235 | −0.0672 | 0.1260 | −0.0071 | −0.0619 | −0.0270 |
| AR(1) φ=−0.5 | −0.4884 | −0.4624 | −0.0167 | −0.0446 | −0.0096 | −0.0260 | −0.1972 | −0.0641 |
| heavy-tailed | **−0.8699** | **−0.8581** | −0.0558 | −0.0107 | 0.0348 | 0.0742 | −0.8021 | −0.0293 |
| right-skewed | −0.5664 | −0.5441 | −0.1058 | −0.0464 | −0.0471 | −0.1463 | 0.0497 | −0.3631 |
| left-skewed | −0.5664 | −0.5441 | 0.1058 | 0.0464 | 0.0471 | 0.1463 | 0.0497 | 0.3631 |
| two-point | **−0.9899** | **−0.9619** | −0.1362 | 0.1815 | −0.0755 | 0.0538 | **0.9899** | 0.1512 |
| trending | −0.6603 | −0.6432 | 0.0710 | −0.0957 | −0.0199 | −0.1259 | 0.0763 | 0.0008 |

Read the last two rows as the limit and not as the headline. On a **two-point**
frame — where the returns take exactly two values — "how many are above the
mean", "the mean" and "the skewness" are ONE statistic, and the column reads
0.9899 against the window mean. On a **heavy-tailed** frame it is
DISCLOSE_GAP-sized against a shipped column. On the four market-shaped frames
it sits at −0.46 … −0.66. BIST daily data carries many exactly-zero returns,
so the two-point row is the shape a consumer should check against their own
universe.

Independent confirmation that this is what the column orders: over **20,000
independent** 20-return windows spanning skewness −3 … +3, Spearman against
the windows' own skewness is **−0.8137**. (That figure, and §6's distribution
table, are computed on the STATISTIC rather than through the function — 20,000
one-window calls would say the same thing slowly. §A1's 1,480-of-1,480
bit-equality is what carries them to the shipped column.)

### What the screen measured on REAL frames, and what it does not cover

Those nine rows are **synthetic**. The 2026-10-24 screen ran a stage-2 fork
overlap of this candidate on real frames, and its row
(`docs/issues/screen/fork_overlap.csv` line 72, local to the owner's machine,
gitignored) is

```
ts_above_mean_20,0.2405,qqe:QQEs_14_5_4.236,0.2476,qqe:QQEs_14_5_4.236,new
```

— max |ρ| **0.2405**, per-frame max median **0.2476**, verdict `new`, i.e.
not a restatement at the 0.90 line. `docs/issues/screen/fork_overlap.py`
computes every `Category` indicator at its defaults over 12 frames (minus
`cdl_pattern`), keeps the output columns that are unchanged under price ×8
and non-constant, and takes the maximum. Since §A7 shows the port and the
screened prototype are bit-equal, that figure carries to this module.

⚠ **It does not bound the overlap with `OSAP_RETSKEW_21`, which is the
column this section is about.** `pandas_ta/statistics/osap_retskew_21.py`
landed on **2026-11-02** (issue #36), nine days AFTER that screen, so it was
not in `Category` and cannot have been in the comparator set. The
−0.6141 / −0.8581 / −0.9619 above are therefore the only measurement of that
pair that exists, and they are synthetic. Gate E's 687 engine comparators
hold no pandas_ta port either, so **the real-data overlap between
`TS_ABOVE_MEAN_20` and `OSAP_RETSKEW_21` specifically is unmeasured.** A
consumer putting both in one model should measure it on their own universe
first.

### The adverse real-frame number, which is in the same run

The same script also wrote candidate-versus-candidate pairs with pooled
|ρ| ≥ 0.80, and `docs/issues/screen/cand_pairs.csv` line 39 is

```
ts_above_mean_20,ts_medskew_20,0.8428
```

`ts_medskew_20` (`docs/issues/screen/candidates.csv` line 82) is tsfresh's
`symmetry_looking` in continuous form — `(mean − median) / std` on 20 returns
— i.e. another skewness reading of the SAME window. **0.8428, pooled, on the
screen's real frames.** That is DISCLOSE_GAP-band and it is the most adverse
number about this candidate anywhere in the owner's tracker.

Three things keep it from being a reason to revert, and all three are checks
a reader can make rather than assurances:

* `ts_medskew_20` is **not shipped** — it is a prototype, candidate issue
  `097-ts-medskew-20` (GitHub #98), with no module in `pandas_ta/`. So it is
  not an in-fork overlap today; it is a flag for whoever ports it.
* Gate E's bands are measured against the ENGINE's 687 columns, and both
  candidates cleared that line independently (this one 0.3594 vs
  `PVT_Slope_norm`, `ts_medskew_20` 0.3727 vs the same column).
* It confirms, on real data, the reading this whole section argues from
  synthetic frames: this column is a coarse skewness statistic. It is
  corroboration of the disclosure, not a contradiction of it.

**If issue #98 ships `ts_medskew_20`, these two columns need a decision**, and
0.8428 is the number that decision starts from.

A second reading of the same statistic is on record in the screen's own
drop list: `docs/issues/screen/skipped.py:125` drops `ts_count_below_mean`
as "1 - ts_above_mean_20 (ties aside)". The owner read this column the same
way it is described here.

## 6. What it actually orders

### Level

Over 20,000 independent windows of iid returns:

| returns | mean | median | sd | p10 | p90 |
|---|---|---|---|---|---|
| gaussian | 0.4999 | 0.5000 | 0.0676 | 0.40 | 0.60 |
| student-t(2) | 0.4991 | 0.5000 | 0.1374 | 0.35 | 0.65 |
| right-skewed (exponential) | 0.3771 | 0.4000 | 0.0696 | 0.30 | 0.45 |
| left-skewed | 0.6229 | 0.6000 | 0.0689 | 0.55 | 0.70 |

Any SYMMETRIC distribution sits at 0.5, and the reason is a REFLECTION, not
"mean = median" (a skewed law can have those equal and still not read 0.5):
if the returns are iid and symmetric about `u`, then `x → 2u − x` preserves
the law, maps the window mean to its own reflection and swaps the above-mean
and below-mean counts, and ties have probability 0 — so E[count above] =
`length`/2 whatever the tails do. The tails change only the spread (sd 0.0676
gaussian against 0.1374 for t(2)), not the centre. That is the whole signal:
the column moves off 0.5 with skew.

### Coarseness and persistence

19 values exist at `length` 20. On the 1,500-bar walk **10** of them appear,
with 0.50 taking **402 of 1,480** bars; 0.50 is the modal value on six of the
nine frames. Neighbouring windows share 19 of their 20 returns, so the column
autocorrelates at **0.8323 / 0.5937 / 0.3495 / 0.1300** at lags 1 / 5 / 10 /
20. It is a state, not an event flag.

## 7. Cost

Traced peak and wall time on 400,000 bars, best and worst of three in ONE
run. ⚠ The memory peaks are the claim and they reproduce exactly; the
milliseconds are this machine's and have moved by up to 7% between runs of
this script, so read them as an order of magnitude and a shape, not as a pin.

| `length` | peak | time (one run) |
|---|---|---|
| 3 | 29.2 MB | 47.6–48.5 ms |
| 20 | 29.2 MB | 73.2–74.3 ms |
| 60 | 29.2 MB | 108.5–112.9 ms |
| 250 | 29.2 MB | 260.6–264.9 ms |

The peak does not grow with `length`, and that is a deliberate spelling. The
count is one `(rows,)` comparison per window POSITION in a Python loop of
`length` iterations, not the one-liner `(windows > mean[:, None]).sum(axis=1)`
which materialises a `(rows, length)` bool array. Both give identical counts
(checked at `length` 20, 60 and 250 on 400,000 bars); only the cost differs:

| `length` | matrix form | by-column form (shipped) |
|---|---|---|
| 20 | 11.3 MB, 27.6 ms | **6.9 MB, 23.4 ms** |
| 60 | 27.3 MB, 45.3 ms | **6.9 MB**, 53.6 ms |
| 250 | 103.3 MB, 170.9 ms | **6.9 MB**, 204.4 ms |

At the shipped default the by-column form wins on both axes; at a long window
it trades ~20% of the time for 15× the memory. `tests/test_ts_above_mean_20.py`
pins the spelling, because the two are behaviourally identical and only the
cost separates them.

The window-by-window oracle this was checked against is 0.12 s on 20,000 bars
where the module is 3.2 ms, which is why it lives in the measure script.

## 8. Gate F — suites

Re-run by the receipt session of 2026-11-13, after the ledger row landed.

`tests/test_ts_above_mean_20.py`: **166 passed** (2.4 s), and 166 passed again
with `AVX512F`, `AVX512_SKX`, `AVX2` and `FMA3` dispatch disabled, via
`docs/measure_ts_above_mean_20_cpu.py`. (165 at the porting commit: the test
asserting the ledger carried NO row is gone, replaced by two that pin the row
that is now there.)

Full suite, `python -m pytest -q`: **3 failed, 7,066 passed, 85 skipped** in
179 s. The three are the two `CLAUDE.md` Known breaks —
`tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` and
`tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`,
both deselected by name in CI — plus one Gate E row that is still owed, and it
is no longer this port's. The launcher re-runs both repos' suites in clean
worktrees.

⚠ `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
now reports exactly `['mtd_ret']` — issue #206's, owed on `dev` — where at the
porting commit it reported `['mtd_ret', 'ts_above_mean_20']`. That remaining
failure is the owed-row mechanism working (`GATE_E_PENDING_OK=1` on the way to
`dev`) and is not about this column.

⚠ **A pre-existing ordering hazard this port's `CATEGORY_TOTAL` bump brushes
against, not caused by it.** `python -m pytest tests/test_wiring_accessors.py
tests/test_altport2_ports.py` fails with "Category total 327, expected 330":
`pandas_ta/core.py:453` hands out the LIVE `Category[name]` list and
`core.py:692` removes names from it, so any earlier category-mode
`df.ta.strategy()` shrinks the global registry for the rest of the process.
Alphabetical collection puts `test_altport2_ports.py` first, so the full suite
and CI are green, and the pinned total is correct — but it is correct by
ordering. The one-line fix is to hand out a copy at `core.py:453`; that is a
behaviour change to `strategy` and outside this issue's allowed scope, so it
is recorded here rather than made. The same defect is recorded in commit
`d30b226` (issue #95).

## 9. Gate E — MEASURED, SHIP

Run **`is97-ts_above_mean_20-5d78f565`**, measured **2026-11-13** by
issue-solver on the module at this branch's HEAD
(`module_sha1 9d0484a70d03c1df4fe6b6ec9f1e36a839dd7507`). Default parameters
(`kwargs {}`), 89 ALTPORT-1 BIST frames, **398,849** pooled bars, **687**
comparators (329 `compute_all` + 358 `ml_features` manifest), canary
`AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS bit-equal`, pandas 2.3.3 / numpy
1.26.4, data stamp `1be6495e`. Bands: `r3-perframe-0.90`.

**`TS_ABOVE_MEAN_20` → SHIP.** Pooled max |ρ| **0.35937568662749647**
(ρ = −0.3594) against `PVT_Slope_norm` of the manifest set at
**n = 396,970**; per-frame max median **0.3580864882804631** against the same
comparator over 89 frames. Over the `compute_all` set alone the maximum is
**0.2757739752658469** against `QQE_RSIMA` at n = 397,069. Both are far under
the 0.76 ship line, and the gap to the 0.90 strike line is not close.

Pooled top five (`top25.csv`), all from the manifest set:

| comparator | ρ | \|ρ\| | n |
|---|---|---|---|
| `PVT_Slope_norm` | −0.35937568662749647 | 0.3594 | 396,970 |
| `PVT_Slope_norm_Pctl` | −0.33359970463205696 | 0.3336 | 391,719 |
| `PVT_Slope_norm_State` | −0.31657291979466284 | 0.3166 | 391,719 |
| `OBV_Price_Divergence` | +0.3031756274449332 | 0.3032 | 397,058 |
| `OBV_Price_Divergence_Pctl` | +0.2921864675278119 | 0.2922 | 392,786 |

Per-frame, the same five (`perframe.csv`, 89 frames each):

| comparator | median | mean | max | min | ≥0.90 | ≥0.80 |
|---|---|---|---|---|---|---|
| `PVT_Slope_norm` | 0.3581 | 0.3422 | 0.5230 | 0.0400 | 0.0% | 0.0% |
| `PVT_Slope_norm_Pctl` | 0.3264 | 0.3209 | 0.4968 | 0.0588 | 0.0% | 0.0% |
| `PVT_Slope_norm_State` | 0.3117 | 0.3040 | 0.5097 | 0.0607 | 0.0% | 0.0% |
| `OBV_Price_Divergence` | 0.3190 | 0.3203 | 0.5312 | 0.1870 | 0.0% | 0.0% |
| `OBV_Price_Divergence_Pctl` | 0.2977 | 0.3007 | 0.4555 | 0.1062 | 0.0% | 0.0% |

**No single frame of the 445 (5 comparators × 89) reaches 0.80**, and the
largest single-frame reading anywhere in that table is 0.5312. The 25th and
last row of `top25.csv` is `apo_pct` at 0.2600, so the whole visible tail
sits between 0.26 and 0.36. One of the 687 comparators was degenerate —
`squeeze_SQZ_NO`, constant over the pooled sample (`degenerate.csv`).

### Did the screen's prototype figures carry over? To every digit it published

Issue #97 quotes the 2026-10-24 screen on the PROTOTYPE as max |ρ| 0.3594 vs
`PVT_Slope_norm` at n = 396,970 with a top-5 per-frame max median of 0.3581.
This run on the PORT lands on the same comparator, at the same n, and its two
figures round to those same four decimals (0.35937568… → 0.3594,
0.35808648… → 0.3581). The screen's rounded values are all that exists here,
so **this is agreement to four decimals and not bit-equality** — the finer
comparison cannot be made from the inputs available to this session.

That n is equal is worth one line, because §A7 measures the prototype firing
one bar EARLIER per frame (bar 19 against bar 20), which would give it 89 more
bars. This column's own non-NaN count is 397,069 while the pooled Spearman
uses 396,970, i.e. `PVT_Slope_norm` is itself NaN on 99 of the bars this
column reports; the simplest reading is that it is NaN at bar 19 of every
frame too, so the prototype's extra bars drop out of the pair. **That reading
is an inference, not a measurement**: the screen's own run outputs are not in
this worktree.

### What this run does NOT settle

* **The overlap with the shipped `OSAP_RETSKEW_21`** (§5) stays
  SYNTHETIC-ONLY. No `OSAP`, `RETSKEW` or `SKEW` column appears anywhere in
  the run's four output files — Gate E's comparators are the ENGINE's columns
  and hold no pandas_ta port — so −0.6141 / −0.8581 / −0.9619 remain measured
  on a walk, a heavy-tailed frame and a two-point frame.
* **The 0.8428 pair with the screen's `ts_medskew_20` candidate** (§5) is
  untouched for the same reason, and `ts_medskew_20` is still unshipped
  (issue #98). This run says what this column does against the engine, not
  what it does against another skewness reading of the same window.
* **Non-default `length`.** `docs/gate_e_ledger.py record` refuses a run with
  non-default parameters, so the row and this section are about `length` 20
  only.

### What the top comparators look like, labelled as a reading

The five above are a volume-price-trend slope, its percentile and its state,
and an OBV/price divergence with its percentile; the rest of `top25.csv` is
21-day return, EFI, SMI, RSI, CMO, TSI, z-score, PPO and APO — momentum and
return-direction readings, at 0.26 … 0.36 and mostly NEGATIVE. **That grouping
is read off their names, and it is an interpretation.** It sits beside §D5's
measurement that the COUNT is invariant to any affine map of the returns, and
beside §5's synthetic Spearman of 0.0699 against the window's mean return and
−0.0746 against its standard deviation: on real BIST data this column is
further from being orthogonal to direction than those two synthetic numbers
would suggest, and the sign is the backwards one §6 describes. Both are
recorded; neither is reconciled here.

The receipt session fills in the measured numbers and the ledger row here.
