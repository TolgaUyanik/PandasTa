# `ts_strike_20` — measured

Issue #90 (TS-STRIKE-20), ported 2026-11-12 on branch `issue-90-ts-strike-20`.
Column: **`TS_STRIKE_20`**, `pandas_ta/statistics/ts_strike_20.py`.
**Status: shipped — Gates A–E cleared** (Gate E measured 2026-11-15 by the
launcher, run `is90-ts_strike_20-7d84c7e5`: max \|ρ\| 0.1856 vs `DMN`, SHIP;
row recorded in `docs/gate_e_ledger.csv`). Gate F is run by issue-solver in
clean worktrees.

Every number here is printed by `python docs/measure_ts_strike_20.py` (its
sections can be run one at a time, e.g. `… gate_b`) on pandas 2.3.3 / numpy
1.26.4, or by `python -m pytest tests/test_ts_strike_20.py -q` — **except the
cross-port figures, each named on its own line with the file it came from**
(`ts_c3_20`'s drift Spearman and `lean_hurst_100`'s drift tolerance in
§Invariances, `ts_binent_20`'s traced peak in §Cost, and the pooled
398,849-bar denominator in §Gate C). Nothing in this file was typed from
expectation; where a number is *not* measured here, the line says so.

## What it is

    r[t]      = close[t] / close[t-1] - 1
    mu        = mean of r over the trailing `length` returns
    span      = max(r) - min(r) over the same window
    column    = longest run of consecutive (r[i] > mu), or 0 when
                span <= 9.09e-13

At the default (`length=20`): the longest unbroken stretch of returns that beat
the average of the 20 returns around them. The window reads 21 closes.

The output is a small **integer**, not a continuous statistic — see *The
attainable set*. Because every sample is compared with the mean of its **own**
window, the column is invariant to any affine map of the returns (see
*Invariances*), which means it is **neither a volatility nor a trend feature**:
what it reads is the *clustering* of above-average returns.

## Source, and what "tsfresh (MIT)" does and does not mean here

The issue names tsfresh's `feature_calculators` (MIT) and states the formula:

> `longest_strike_above_mean on 20 returns`

with the screen prototype (`docs/issues/screen/ind_screen.py`, candidate
`ts_strike_20`) spelling it as

    roll(ret(c), 20, w_longest_strike_above_mean)

    def w_longest_strike_above_mean(W):
        b = W > W.mean(1, keepdims=True)
        cur = np.zeros(len(W)); best = np.zeros(len(W))
        for j in range(W.shape[1]):
            cur = np.where(b[:, j], cur + 1, 0)
            best = np.maximum(best, cur)
        return best

⚠ **tsfresh is not installed in this worktree and web access is unavailable.**
So "tsfresh (MIT)" is an *attribution* to a feature NAME, exactly as issue #90
says ("Library code (tsfresh, MIT): existence, not evidence") — it is not an
oracle this session could run. The formula under test is the issue's line and
the prototype. **Nothing in this port describes tsfresh's source text**: how it
spells the comparison, how it counts runs, what it does with an empty series or
with NaNs is unverified here. The 20 is the issue's own parameter.

What *is* checked independently is the run counting, against a spelling chosen
for its independence rather than for any claimed resemblance to tsfresh's: an
`itertools.groupby` run-length pass over `r > mean(r)`, applied window by
window in a plain Python loop over explicit slices, shares no array machinery
with the module and is bit-equal to it on every fired bar of three frames
(§Gate A, A3).

## Gate A — correctness

### A1 — windows whose answer is derived by hand

Each case is a list of **returns**; the closes handed to the module are
`cumprod(1 + r)`, so the module's own return arithmetic is what maps one to the
other. The answer comes from the definition, with no implementation involved.

| `length` | returns | mean | hand answer | module |
|---|---|---|---|---|
| 8 | `[0,0,1,1,1,0,0,0]` | 3/8 | 3 | **3** |
| 8 | `[1,0,1,0,1,0,1,0]` | 1/2 | 1 | **1** |
| 8 | `[0]*8` | 0 | 0 (nothing is *strictly* above) | **0** |
| 8 | `[5]*8` | 5 | 0 (same, and not 8) | **0** |
| 8 | `[1]*7 + [0]`| 7/8 | 7 = `length − 1` | **7** |
| 8 | `[0] + [1]*7`| 7/8 | 7 (run at the other end) | **7** |
| 8 | `[1,1,0,1,1,1,0,1]` | 6/8 | 3 (runs 2, 3, 1) | **3** |
| 20 | `[0]*8+[1]*5+[0]*3+[1]*2+[0]*2` | 7/20 | 5 (runs 5, 2) | **5** |

The last row is at the **shipped** length. Every case also pins the warm-up:
`length` NaNs, first value at bar `length`.

### A2 — the screen prototype

On a 1,500-bar gaussian walk, against the prototype retyped from
`ind_screen.py`:

| | result |
|---|---|
| bit-equal on fired bars | **1480 / 1480** |
| max \|difference\| | 0.0 |
| Spearman | 1.000000 |

The prototype **imported** out of the owner's tree (`REG["ts_strike_20"]["fn"]`,
present here because this worktree carries a read-only copy of the gitignored
`docs/issues/`) gives the same 1,480 of 1,480.

⚠ **One bar differs, and it is a warm-up bar.** The prototype windows the whole
return array, including the undefined first return, so its first window (bar
19) has a NaN mean, every comparison against NaN is False, and it reports a
strike of **0.0**. This module reports **NaN** there, because that window does
not have 20 returns. Measured: the NaN masks differ at exactly bar `[19]`, the
prototype fires **1,481** bars and the module **1,480**. Pinned by
`test_the_prototype_fires_one_extra_warmup_bar_and_this_module_does_not` so it
cannot drift into a correctness claim later.

### A3 — an independent `groupby` spelling, window by window

`max(len(run) for run of True in groupby(r > mean(r)))`, in a plain Python loop
over explicit slices — no numpy windowing, no vectorised run counting, so it
shares no machinery with the module. The spelling is chosen for that
independence; **whether tsfresh spells it this way is unverified in this
session** (not installed, no web access):

| frame | bit-equal | NaN masks agree | windows reaching the noise floor |
|---|---|---|---|
| gaussian walk | **1480 / 1480** | yes | **0 of 1,480** |
| tick-rounded walk | **1480 / 1480** | yes | **0 of 1,480** |
| AR(1) returns, φ = +0.6 | **1480 / 1480** | yes | **0 of 1,480** |

The oracle carries **no** noise floor — it does not import `NOISE_FLOOR` or
re-implement the guard — so the last column is what makes the first one
evidence rather than a shared branch: on these frames the module's one addition
to the oracle never fires. Asserted in the same test, not just printed.

### A4 — the attainable set, constructed

* Every k from **1 to 19** is reachable at `length=20`: a window of k
  consecutive `+1` returns among `20 − k` zeros has mean `k/20`, so exactly
  those k are above it. All 19 constructed and checked.
* **`length` itself is unreachable.** Not measured — proved: a window's samples
  cannot all be strictly above their own mean.
* **0 means the returns are all equal, or equal to rounding level.** The first
  half is the same argument the other way: if they are not all equal, the
  maximum is strictly above the mean, so some run exists — that proof covers
  the unguarded formula. The second half is the floor's doing and is measured
  in *The rounding-noise floor*: a window whose return span is at or below
  9.09e-13 also reads 0, even where the unguarded answer is 8..11.
* 200,000 independent iid-gaussian 20-return windows produce values **1..12**
  (counts 595 / 32,999 / 72,666 / 51,856 / 25,097 / 10,517 / 4,134 / 1,443 /
  487 / 164 / 36 / 6), mean 3.6379, median 3, and **0 windows at 0** and **0 at
  20**.

### A5 — five readings the wording leaves open, decided and priced

Each number from the same 1,500-bar walk, port against variant, 1,480 shared
bars.

| rejected reading | bit-equal | max \|diff\| | Spearman | verdict |
|---|---|---|---|---|
| `>=` instead of `>` | 1480/1480 | 0 | 1.000000 | rejected on the degenerate case, below |
| log returns | 1455/1480 | 3 | 0.988879 | a different column |
| longest strike **below** the mean | 346/1480 | 6 | 0.109170 | a different column |
| divided by `length` | 0/1480 | 8.55 | 1.000000 | a strict rescaling |
| 0 rather than NaN on a degenerate window | — | — | — | see *The rounding-noise floor* |

* **Strict `>`**, which is what the issue's line ("above their mean") and the
  prototype's `W > W.mean(1, keepdims=True)` give. On continuous-ish frames
  `>=` is bit-equal,
  and the reason is measured rather than assumed: an exact tie with the window
  mean happens **0 times in 29,600 samples** on the walk and the same on the
  tick-rounded walk. It is still the wrong reading, because on the one case
  real data reaches — `length + 1` identical closes — every return *equals* the
  mean, so `>=` marks all 20 and reports **20**, the top of the scale, where
  this column reports **0**, the bottom. Maximal disagreement on exactly the
  reachable case.
* **Simple returns**, the prototype's `ret`. Log returns are a *monotone but
  non-affine* transform, which moves the window MEAN — the thing the
  comparison is against — so this is not a no-op the way it would be for a
  rank statistic: 25 of 1,480 bars move, by up to 3 runs.
* **Above, not below.** The screen's own inventory lists the mirror as a
  separate candidate it dropped (`skipped.py`:
  `("ts_longest_strike_below_mean", TS, "read: mirror of ts_strike_20")`), so
  the two are not interchangeable readings of one line. Measured, the mirror is
  nearly independent of this column (Spearman 0.109170), so the choice is a
  decision and not a formatting detail.
* **The raw count.** The prototype returns the run length itself, and the
  screen's neighbouring candidate `ts_above_mean_20` spells its own division
  out (`count_above_mean / n`), so the absence of a division here is the
  screen's own distinction rather than an omission. `port / 20` reproduces the
  normalised reading on 1,480 of 1,480 bars, so nothing a rank miner sees
  changes either way.

## Gate B — causality, by mutant

`importlib`-read module source, one textual substitution, `exec`'d in memory.
Six mutants — five on the three standard frames, and a sixth (`forward_span`)
which needs a frame that reaches the noise floor and has its own subsection
below:

| id | mutation |
|---|---|
| `write_shift` | the output back-dated by `length` (`.shift(-length)`) |
| `write_early` | the output written one bar early (`out[length-2:-1]`) |
| `forward_return` | each return attributed to the earlier bar (`r[:-1] = …`) |
| `forward_mean` | each window compared with the NEXT window's mean |
| `forward_window` | the above/below pattern taken from the next window |
| `forward_span` | the guard's `span` taken from the next window (own frame, below) |

Sweep: 37 offsets J = 40, 80, … 1480. For each J every bar from J onward is
replaced by a different path; a **hit** is any J at which something strictly
before J moved.

| frame | real module | `write_shift` | `write_early` | `forward_return` | `forward_mean` | `forward_window` |
|---|---|---|---|---|---|---|
| walk | **0/37** | 37/37 | 36/37 | 36/37 | 36/37 | 36/37 |
| tick-rounded | **0/37** | 36/37 | 33/37 | 33/37 | 34/37 | 33/37 |
| AR(1) φ=+0.6 | **0/37** | 37/37 | 37/37 | 37/37 | 37/37 | 37/37 |

At two non-default lengths, on the walk:

| `length` | real module | `write_shift` | `write_early` | `forward_return` | `forward_mean` | `forward_window` |
|---|---|---|---|---|---|---|
| 5 | **0/37** | 37/37 | 36/37 | 36/37 | 36/37 | 36/37 |
| 60 | **0/37** | 37/37 | 33/37 | 33/37 | 34/37 | 33/37 |

Every mutation is asserted live (its output differs from the real module's at
the same settings), and the real module leaks **0 of 37** in all six
configurations run — the five above plus the flat-planted frame the sixth
mutant needs.

### Why some cells are under 37/37, measured rather than excused

**A one-bar look-ahead can move exactly ONE bar of the prefix.** Bar J − 1 is
the only bar whose window reaches `close[J]`; nothing earlier does. Measured
for all four one-bar mutants on the walk and on the tick-rounded walk: across
the 37 offsets the set of moved prefix bars is always either `()` or `(J-1,)`,
and never anything else. So a cell under 37/37 is an offset where that **single
integer** happened not to change — and what it would have had to cross is a
whole unit, not an ulp.

That is reachable because the column is coarse. Measured: consecutive bar pairs
carrying the *same* value — walk **1,153 of 1,479**, tick-rounded **1,079**,
AR(1) **910**. This is a limit of the sweep, stated as such: a one-bar leak in
this column is invisible at any offset where bar J − 1's integer is unchanged,
and the sweep's power comes from running 37 of them.

Two further specifics:

* `length=60`'s missed J = 40 is below the 60-bar warm-up: both prefixes are
  entirely NaN there, so there was nothing to move.
* `write_shift` on the tick-rounded frame misses J = 40 for a different reason,
  and it is the one coincidence in the table: the mutant's 40-bar prefix shows
  the real module's bars 20..59, and all 40 of those integers come out
  identical on the two paths (`[4]*8, 3, 4, [5]*5, [4]*17, [3]*8`) although
  closes 40.. differ (122.79 → 117.34 at bar 40). Printed in full by
  `… gate_b` under *the mechanism*; the same mutant is 37/37 on both other
  frames.

### The sixth mutant — the `span` that decides the guard

`span` is the module's other windowed input, and the five mutants above do not
touch it. Taking it from the *next* window is a no-op on a continuous frame,
because the floor never fires there (measured: **0 of 1,480** windows reach it
on each of the three frames, printed beside §Gate A, A3). So the sweep for this
one runs on a walk carrying 21 identical closes **ending at each offset J** —
runs of 21, 40 apart, so they do not overlap — where **37** bars read 0:

| frame | real module | `forward_span` |
|---|---|---|
| walk | — | 1 bar moves, printed as index **[1499]** — the last bar of a 1,500-bar frame, where `np.roll` wraps the warm-up window's NaN span round; no guard crossing |
| flat-planted | **0/37** | **37/37**, 38 bars moved (indices 39, 79, 119, … 1499) |

Pinned by `test_the_span_that_decides_the_guard_is_causal_too`. Without that
frame the mutant would have been reported as uncaught-but-harmless, which is
exactly the kind of silent gap this file is supposed to close.

`offset` is the caller's own look-ahead and not a property of the formula:
`offset=2` equals `base.shift(2)` and `offset=-2` equals `base.shift(-2)`,
both exactly. The sweep covers the default `offset=0`.

## The rounding-noise floor

The returns of an **exactly geometric** path are mathematically constant, so
the answer is 0. In float64 they differ in their last bits, and an unguarded
reading then reports the longest run *of that noise*:

| frame (300 bars) | guarded | unguarded |
|---|---|---|
| 1%-a-bar ladder | 0.0 on all 280 fired bars | **1, 2, 3, 4** on 280 bars (counts 85 / 64 / 80 / 51) |
| exact ×1.5 ladder | 0.0 on all 280 | **1, 2, 3, 5, 8** (counts 234 / 25 / 18 / 1 / 2) |

⚠ **Those unguarded values and counts are rounding noise, so they are not
portable.** Re-measured 2026-11-15 with
`NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` (numpy's kernels on a
runner without AVX-512), the 1%-a-bar ladder gives the same four values with
counts **87 / 75 / 73 / 45** and the ×1.5 ladder is unchanged. The table above
is this machine's run. What `tests/test_ts_strike_20.py` asserts is therefore
the structural part only: all 280 fired bars nonzero, and every unguarded value
a value the column takes on a real walk.

⚠ **This is why the floor matters more here than it did for `ts_c3_20`.** That
column's unguarded failure reached 8.0e+41 and could not be missed. Here every
unguarded value — 1 to 8 — is *inside the live range of a real walk* (1 to 9,
§Gate C), so nothing downstream could have spotted it. The window's return span
on those ladders is 6.661e-16 and 4.441e-16 against a floor of 9.095e-13.

**On real-shaped data the floor costs nothing.** Against the unguarded form on
300-bar frames: walk 280/280 bars bit-equal, tick-rounded 280/280, NaN masks
equal, no value changed.

**What it does cost, measured.** On a monotone one-tick-per-bar path the
returns genuinely *decrease* — a fixed tick is a shrinking fraction of a rising
price — so about half the window sits above its mean and the mathematical
answer is near 10, not 0:

| path | window return span | guarded | unguarded |
|---|---|---|---|
| price 50, tick 0.01 | 6.793e-07 | **10** on every fired bar | 10 |
| price 1e6, tick 0.001 | 2.220e-16 | **0** | every value from **0 to 19** |
| price 1e6, tick 0.01 | 1.998e-15 | **0** | 8, 9, 10, 11 |

The first row is the floor *not* firing on real variation. The second is the
floor doing its job: the unguarded answer there is not "about 10", it is the
whole scale. The third is the honest cost — the unguarded form reads 8..11, a
4-value spread around the mathematical answer, and the column reports 0
instead. At a return span of 2e-15 (two ulps of a 1e-8 return) there is nothing
left to read a *pattern* from, which is the trade this port takes.

The floor is an **absolute constant** (4096 eps = 9.094947e-13), not a rolling
quantity, because what it bounds is the range of *dimensionless* price ratios —
so it has no window of its own whose causality would need pinning. The module
contains **one** `sliding_window_view` call and **no** `.rolling(` at all,
asserted by `test_the_noise_floor_is_an_absolute_constant_and_the_module_has_no_rolling`.

Unlike `ts_c3_20` and `ts_binent_20`, a degenerate window here is **0, not
NaN**, because 0 is the value constant returns actually imply: nothing can be
strictly above their mean. What 0 means is therefore two things, not one: **0
is unreachable for a window whose return span clears the floor**, so on
continuous data it is unambiguously "the returns are equal" — but below the
floor it also covers a window that is flat only *to rounding level*, which is
the cost priced in the table above (price 1e6, tick 0.01: span 1.998e-15,
returns genuinely decreasing, unguarded 8..11, column 0).

## The attainable set — an integer count

| | |
|---|---|
| range | `{0} ∪ {1 … length − 1}`, i.e. 20 values at the default |
| 0 | ⇔ the window's `length` returns are all equal (to rounding level) |
| `length` | unreachable, by proof |
| observed on a 1,500-bar walk | **9** distinct values, 1 … 9 |
| observed on a tick-rounded walk | **9**, 1 … 9 |
| observed on an AR(1) φ=+0.6 path | **11**, 2 … 12 |
| observed over 200,000 iid windows | **12**, 1 … 12 |

So the column **ties heavily by construction** — 1,480 bars over 9 distinct
values — and a rank statistic over it carries many tied ranks.

That is also why `docs/IndicatorDictionary.md` tags it **`ORD`** rather than
`SF`. The tag is not a property of the column in general: it is decided by the
generator's own fixed probe frame (`docs/gen_indicator_dictionary.py`,
`N = 600`, rule at line 147 — "≤ 12 distinct integer values ⇒ ordinal"), and
on that frame the column clears the rule. The measurements above are *near* the
rule's boundary rather than safely inside it — 200,000 iid windows produce
exactly 12 distinct values, with 36 and 6 bars in the top two buckets, and that
tail grows with n — so a longer frame could take the probe past 12 and flip the
tag to `SF`. Nothing here claims it stays `ORD` on an arbitrary frame.

## Invariances — what the column does NOT see

Every sample is compared with the mean of its own window, so `r → a·r + b` with
`a > 0` cannot change which samples are above it. Measured on the 1,500-bar
walk, 1,480 fired bars:

| transform | bit-equal |
|---|---|
| returns × 0.5 | **1480 / 1480** |
| returns × 3 | **1480 / 1480** |
| closes × exp(0.004·t) (+0.4% log drift a bar) | **1480 / 1480** |

Drift is an affine map of the returns — `close·e^{dt}` gives
`r → e^d·r + (e^d − 1)` — which is why the third row is exact and not merely
close. Worth knowing because the two nearest statistics ports differ:
`ts_c3_20` is **not** drift-invariant (Spearman 0.801318) and
`lean_hurst_100` is invariant only to 2.4e-15. ⚠ Those two figures are
**borrowed**, not re-run here: both come from `docs/TsC320Measured.md`
§Invariances (lines 329 and 331), measured in issue #88's session.

Two consequences, pinned as tests:

* **Not a volatility feature.** The same pattern at any amplitude reads the
  same integer.
* **Not a trend feature.** A pure geometric trend has *constant* returns, so it
  reads **0** — the bottom of the scale (measured: 0.0 on all 280 fired bars of
  a 1%-a-bar ladder). A path alternating up and down every bar reads a constant
  **1** on all 1,480 fired bars. Both deterministic extremes sit at the bottom;
  the column is about clustering, not direction.

## Gate C — reachability

**Real data, measured 2026-11-15** by the launcher's Gate E run
`is90-ts_strike_20-7d84c7e5` over the 89 frozen ALTPORT-1 frames: non-NaN
**397,069** of 398,849 pooled bars, non-zero **397,069**. The 1,780 empty bars
are exactly the arithmetic floor `89 × 20` — one warm-up per frame and nothing
else, so no frame on the universe carries a bad close or an overflowing close
pair. Two bad-data causes could have emptied more, each measured on synthetic
frames below: a close inside a frame that is NaN, zero, negative or subnormal
(**21 bars each** — one bad close spoils two returns), and a close PAIR whose
ratio overflows (**20 bars** — one spoiled return). Neither occurs here.

Note what is **not** a NaN cause for this column: a degenerate window. 21
consecutive identical closes (a halted or limit-locked session), an exactly
geometric window and a near-monotone fine-tick window at a high price all read
**0** rather than NaN, so they would show up in the *non-zero* count and not in
the NaN count. The porting session expected the non-zero count to sit below the
non-NaN count by however many such windows the 89 frames carry; measured, the
two counts are **equal**, so not one of the 397,069 fired bars on the universe
reads 0 — no window of 21 BIST daily closes in these frames is flat to the
9.09e-13 floor.

The rest of this section is **synthetic**: 1,500-bar generated paths, 1,480
fired bars each.

| path | fires | non-zero | distinct | min | max | median | mean |
|---|---|---|---|---|---|---|---|
| gaussian walk | 1480/1500 | 1480 | 9 | 1 | 9 | 3 | 3.6912 |
| tick-rounded walk | 1480/1500 | 1480 | 9 | 1 | 9 | 3 | — |
| AR(1) φ=+0.6 | 1480/1500 | 1480 | 11 | 2 | 12 | 5 | 5.5128 |
| alternating up/down | 1480/1500 | 1480 | **1** | 1 | 1 | 1 | 1 |

`0 < 1480 < 1500` on every frame, and 1,480 of 1,480 fired bars are non-zero,
so Gate D's non-constant requirement is met on the three random frames. The
**alternating** row is the honest exception: on a frame with no clustering at
all the column is a constant 1, which is pinned by
`test_an_alternating_path_is_a_constant_one_and_says_so` rather than left for a
reader to discover.

Warm-up arithmetic, measured at three lengths on the same 1,500-bar walk:
first value at bar `length`, fired bars `1500 − length` (5 → 1,495, 20 →
1,480, 60 → 1,440).

The full distribution on the walk, since the column is discrete enough to print
in full:

| value | bars | share |
|---|---|---|
| 1 | 1 | 0.07% |
| 2 | 272 | 18.38% |
| 3 | **484** | 32.70% |
| 4 | 366 | 24.73% |
| 5 | 222 | 15.00% |
| 6 | 70 | 4.73% |
| 7 | 53 | 3.58% |
| 8 | 7 | 0.47% |
| 9 | 5 | 0.34% |

**What the column orders is clustering.** AR(1) log-return paths, 1,500 bars
each:

| φ | median | mean | p10 | p90 |
|---|---|---|---|---|
| +0.8 | 6 | **6.5392** | 4 | 10 |
| +0.6 | 5 | **5.5128** | 3 | 8 |
| +0.3 | 4 | **4.3872** | 3 | 6 |
| 0 | 3 | **3.6520** | 2 | 5 |
| −0.3 | 3 | **3.1297** | 2 | 5 |
| −0.6 | 3 | **2.7081** | 2 | 4 |
| −0.8 | 2 | **2.3223** | 1 | 3 |

The **means** are strictly ordered in φ; the **medians tie** at 3 across three
cases, which is the practical consequence of nine reachable values. The test
pins the means' ordering, not the medians'.

**One outlier SHORTENS the strike**, which is the opposite of the reflex: a
single huge return drags the window mean above the ordinary returns, so fewer
of them are above it. Measured on the walk with a +50% return planted at bar
700: the 20 windows holding it average **1.9500** (values 1 and 2) where the
same bars averaged 2.0500 (values 2 and 3) without it, against a frame mean of
3.6912.

## Gate D — scale-free

1,500-bar frames, 1,480 fired bars each, bit-equal counts:

| frame | ×8 | ×64 | ×10 | ×3.7 |
|---|---|---|---|---|
| walk | **1480/1480** | **1480/1480** | **1480/1480** | **1480/1480** |
| tick-rounded | **1480/1480** | **1480/1480** | **1480/1480** | **1480/1480** |
| AR(1) φ=+0.6 | **1480/1480** | **1480/1480** | **1480/1480** | **1480/1480** |

At two non-default lengths, on the walk:

| setting | fired bars | ×8 | ×64 |
|---|---|---|---|
| `length=5` | 1,495 | **1495/1495** | **1495/1495** |
| `length=60` | 1,440 | **1440/1440** | **1440/1440** |

NaN masks are equal in all sixteen cells. ×8 is bit-identical rather than
merely close because every input is a price *ratio*: `8a / 8b` is the same
double as `a / b`, so the whole return series is reproduced bit-for-bit and the
integer cannot move.

⚠ **×10 and ×3.7 come out bit-identical too, and the arithmetic does not
promise that.** Those rescales do not reproduce the returns bit-for-bit, and
the output is an *integer decided by a float comparison*, so a last-bit change
in a return or in the window mean could flip a sample that sits within rounding
of the mean. What makes it hold here is measured:

| frame | smallest \|r − mean of its window\| | as a fraction of the window's return span | exact ties |
|---|---|---|---|
| walk | 1.238e-06 | 2.471e-05 | **0 of 29,600** |
| tick-rounded | 7.669e-08 | 1.610e-06 | **0 of 29,600** |
| AR(1) φ=+0.6 | 5.210e-08 | 1.284e-06 | **0 of 29,600** |

Several orders of magnitude from a rounding decision. The ×10/×3.7 test
therefore asserts **at most one bar may differ** rather than bit-equality: the
measurement is here, and the test does not pretend the margin is a guarantee.

`0 < fires < n` holds on all three frames (1,480 of 1,500) with 9–11 distinct
values and all 1,480 non-zero, so no constant column is passing this gate by
accident.

## Gate E — attribution

**Measured 2026-11-15 by the launcher**, run `is90-ts_strike_20-7d84c7e5`,
`gate_e_overlap.py run --module pandas_ta.statistics.ts_strike_20` against the
code at this branch's HEAD (`candidate_source_sha1` `7045dbf2`,
`pandas_ta_src_sha1` `5a88fdbe`). Universe: the 89 frozen ALTPORT-1 frames,
398,849 pooled bars, 687 comparators (329 `compute_all` + 358 `ml_features`
manifest `1d`), defaults (`kwargs` empty), pandas 2.3.3 / numpy 1.26.4, canary
`AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS bit-equal`. Bands `r3-perframe-0.90`.

| column | max \|ρ\| | against | set | n | per-frame max median | frames ≥ 0.90 | verdict |
|---|---|---|---|---|---|---|---|
| `TS_STRIKE_20` | **0.1856** | `DMN` | compute_all | 397,069 | **0.1852** (`DMN`) | 0 of 89 | **SHIP** |

Pooled and per-frame both sit far under the 0.76 SHIP line, so the column
ships unchanged. The run's best manifest comparator is
`Dist_to_BB_Upper_pct` at **0.1829** over the same 397,069 bars; the run
reports `n_degenerate` **1** (one comparator with no variation to rank
against) and the ledger row is `is90-ts_strike_20-7d84c7e5`, recorded in
`docs/gate_e_ledger.csv` on 2026-11-15.

Against the issue's PROTOTYPE numbers (2026-10-24, run `screen_20261024`,
n = 397,158 — a prototype is not a port): max \|ρ\| 0.1855 vs `DMN`, top-5
per-frame max median 0.1848, next comparators `Dist_to_BB_Upper_pct` 0.1826 and
`ui` 0.1810. The port lands on the same comparator with 0.1856 / 0.1852 over 89
fewer bars — the one warm-up bar per frame that §Gate A, A2 measures as the
only difference between the two spellings.

**Nearest shipped columns on ONE 1,500-bar synthetic walk — NOT Gate E** (12
shipped columns, one frame; Gate E is 687 comparators over 89 frozen BIST
frames):

| \|ρ\| | column | n |
|---|---|---|
| 0.3119 | `lean_momersion_20` | 1479 |
| 0.2105 | `ts_c3_20` | 1480 |
| 0.1691 | `entropy_20` | 1462 |
| 0.1621 | `chop_14` | 1480 |
| 0.1338 | `natr_14` | 1480 |
| 0.0788 | `kurtosis_20` | 1480 |
| 0.0719 | `rsi_14` | 1480 |
| 0.0657 | `tf_centroid_20` | 1480 |
| 0.0408 | `zscore_20` | 1480 |
| 0.0181 | `skew_20` | 1480 |
| 0.0173 | `lean_hurst_100` | 1401 |
| 0.0110 | `ts_binent_20` | 1480 |

`lean_momersion_20` is the column a reader should worry about and it tops this
list: it is the share of consecutive return pairs that keep their direction
(issue #86), which is a *different* reading of the same raw material — return
persistence. One synthetic frame is not evidence about the 89; the issue's own
stage-2 fork overlap put the prototype's worst at 0.1594 vs `ui:UI_14` over 12
frames, and `ui` does not appear in this table's top three. Both are small
enough that the launcher's run is the one that matters.

## Gate F — suites

Porting session, in this worktree:

* `python -m pytest tests/test_ts_strike_20.py -q` → **144 passed**.
* `python -m pytest -q` → **3 failed, 5,954 passed, 83 skipped** (wall clock
  about two minutes; not quoted, for the reason §Cost gives).
  The three failures are the two `CLAUDE.md` *Known breaks* —
  `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`,
  which needs the sibling `../AlternativeRepos` checkout and is deselected in
  CI, and `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`,
  the `supertrend` citation into the untracked `docs/pine/` — plus
  `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, which
  reports `['mtd_ret', 'ts_strike_20']`: the row this port owes, and one owed
  before this branch. CI into `dev` skips that test under
  `GATE_E_PENDING_OK=1`. The same counts are summarised in
  `docs/reviews/auto-2026-11-12-ts-strike-20/99-summary.md`.

⚠ **This count is stale the moment any file in the tree changes, including a
file under `docs/`.** It was invalidated once in this session exactly that
way: review round 3 asked for a reviewer's verdict to be pasted into
`docs/reviews/auto-2026-11-12-ts-strike-20/01-ts-strike-20.md` verbatim, that
verdict quoted two Gate B grids as slash-joined number runs, and
`test_pine_coverage_csv.py::test_no_other_document_retypes_the_split` — which
scans every prose file in the fork for five or more slash-joined numbers —
went red, taking the suite to 4 failed while this line still said 3. Re-run
the suite after touching anything, prose included.

**Fix session, 2026-11-15** (the launcher's CI-CPU check found
`test_an_exactly_geometric_frame_reads_zero_rather_than_a_run_of_noise`
pinning a CPU-dependent detail; see the ⚠ under §The rounding-noise floor):

* `python docs/measure_ts_strike_20_cpu.py disable pytest` → **144 passed**
  under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`, and
  `… native pytest` → **144 passed** on this machine's kernels. The script
  sets the variable before importing numpy and then runs the module in the
  same process, which a shell prefix would also do; it is committed as the
  receipt for the two count sets quoted above.
* `python -m pytest -q` → **2 failed, 10,764 passed, 85 skipped** in
  272.83 s. The failures are
  `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
  (needs `../AlternativeRepos`, deselected in CI) and
  `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`.
  The porting session's third failure,
  `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`, is
  gone: `CLAUDE.md` records it as fixed on 2026-11-15 by #8 (PINECITE),
  which tracked the one `docs/pine/` file its evidence cites. The passed
  count also moved far more than this session's edits explain (5,954 →
  10,764); it is quoted as what this run printed, not reconciled.

**Receipt session, 2026-11-15** (after `docs/gate_e_ledger.py record` added this
port's row):

* `python -m pytest -q` → **2 failed, 10,771 passed, 85 skipped** in 275.79 s.
  The failures are
  `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
  (needs `../AlternativeRepos`, deselected in CI) and
  `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, which
  now reports `['arch_lm', 'diff2_acf1', 'edge', 'firstzero_ac', 'halflife',
  'lumpiness', 'mtd_ret']` — seven rows owed on `dev` before this branch, and
  **`ts_strike_20` is no longer among them**. CI into `dev` skips that test
  under `GATE_E_PENDING_OK=1`.

**Pre-push gate, round 1 fix session, 2026-11-15** (the six pre-rebase wiring
counts corrected in §Five-point wiring, this §Gate F paragraph added, and the
same counts corrected in the two run-folder files):

* `python -m pytest -q --tb=no -rf -p no:warnings` → **2 failed, 10,771
  passed, 85 skipped**, twice: once with the wiring counts fixed (277.30 s)
  and once more after this paragraph itself was written (274.21 s). Same two
  failures and same counts as the receipt-session run above, so these prose
  edits moved nothing.
* `python docs/measure_ts_strike_20_cpu.py disable pytest` → **144 passed**
  again under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`; no
  test code changed in this fix session, and the check is re-run rather than
  assumed.

**Why the launcher's clean-worktree run reads 7 fewer passes and 7 more
skips.** Its number for the same HEAD is 10,764 passed, 2 failed, 92
skipped against this session's 10,771 passed, 2 failed, 85 skipped — the same
10,858 collected either way, so nothing regressed and nothing new is skipped. The 7 are the
tests gated on the owner's gitignored `docs/issues/` tree, which this worktree
carries as a read-only copy and a clean checkout does not. Grepping `tests/`
for a `pytest.skip`/`skipif` whose reason names `docs/issues` finds four
gating sites, and `--collect-only` on them collects exactly 7 node ids:

    tests/test_ts_aggac_60.py::test_the_retyped_prototype_reproduces_the_owners_registry_entry
    tests/test_ts_peaks_20.py::test_the_retyped_prototype_matches_the_owners_registry[walk]
    tests/test_ts_peaks_20.py::test_the_retyped_prototype_matches_the_owners_registry[coarse-grid]
    tests/test_ts_kurt_60.py::test_the_port_is_bit_equal_to_the_screens_own_registry_candidate[_walk]
    tests/test_ts_kurt_60.py::test_the_port_is_bit_equal_to_the_screens_own_registry_candidate[_tick_rounded]
    tests/test_ts_kurt_60.py::test_the_port_is_bit_equal_to_the_screens_own_registry_candidate[_heavy_tailed]
    tests/test_ts_perment_20.py::test_the_retyped_prototype_is_the_screens_own_code

None of them belongs to this port: `tests/test_ts_strike_20.py` carries no
such gate, so its 144 tests run identically in a clone.

The launcher runs both repos' suites in clean worktrees.

## Cost

The module materialises one `(n − length + 1, length)` **boolean** array and
reduces over views of the return array for the mean, the min and the max, so
its memory is O(n · length) — but a byte a cell rather than a double, which is
why the peak here is about a quarter of `ts_binent_20`'s **144.1 MB** at the
same n (`docs/TsBinent20Measured.md` §Cost, line 635 — borrowed from issue
#89's session, not re-run here). The boolean
column below is arithmetic from the shape; the peak is measured with
`tracemalloc`:

| bars | boolean array (computed) | traced peak (measured) |
|---|---|---|
| 400,000 | 8.0 MB | **37.2 MB** |

The traced peak is the figure that reproduces: 37.2 MB on every run of
`… cost` in this session and in review. **Wall-clock is not quoted as a
band**, because it does not reproduce — runs on this machine have landed
between 116 and 165 ms, with the high end a review re-run rather than a
different machine. Order of magnitude: a tenth of a second at 400,000 bars.

## Edge cases, measured

| input | result |
|---|---|
| `length` closes (20) | `None` — `verify_series` wants `length + 1` |
| `length + 1` closes (21) | fires 1 bar, at bar 20 |
| `length` = None, 0, −5, 2, 0.5, 2.9 | falls back to 20 (`TS_STRIKE_20`) |
| `length` = 50.9 | truncates to 50, identical to `length=50` |
| `length` = 3 | `TS_STRIKE_3`, 397 of 400 bars |
| `fillna=-1.0` | fills exactly the 20 warm-up bars |
| close = NaN / 0 / −5 / inf / 1e-310 at bar 200 | each empties **21** bars (200..220); 0 bars before 200 move |
| closes 1e-300 then 1e50 at bars 200, 201 | the ratio overflows: **20** bars emptied (201..220) |
| 20 identical closes planted at bar 200 | **0** bars read 0 (the window's oldest return is still non-zero) |
| 21 identical closes | bar 220 reads 0 |
| 25 identical closes | bars 220..224 read 0 |

The overflow row is why the module filters non-finite returns rather than
comparing them: measured, without the filter those 20 windows would read
**0.0** — an infinite mean leaves nothing strictly above it — so a bad data
pair would be indistinguishable from a *flat* window instead of being missing.

Why `MIN_LENGTH = 3`, measured through the variant harness since the module
refuses those lengths (400-bar walk): `length=1` is a window that IS its own
mean, so the column is **0 on all 399** fired bars; `length=2` puts exactly one
of the two above the mean, so it is **1 on all 398**; `length=3` is the first
that varies (values 1 and 2, counts 271 / 126).

## Five-point wiring

| # | file | state |
|---|---|---|
| 1 | `pandas_ta/statistics/ts_strike_20.py` | the indicator |
| 2 | `pandas_ta/statistics/__init__.py` | `from .ts_strike_20 import ts_strike_20` |
| 3 | `pandas_ta/__init__.py` → `Category["statistics"]` | `"ts_strike_20"` |
| 4 | `pandas_ta/core.py` | `df.ta.ts_strike_20(length=…, offset=…)` |
| 5 | `tests/test_ts_strike_20.py` | 144 tests |

Plus the three documents the counts live in: `README.md` (351 → **352** in
`Category`, 359 → **360** callable, statistics 53 → **54**),
`docs/IndicatorDictionary.md` (regenerated by
`python docs/gen_indicator_dictionary.py`; `TS_STRIKE_20` **ORD**, warm-up 20)
and `docs/MLCompanionContract.md` (696 → **697** tagged columns, 54 → **55**
`ORD`), and `tests/test_altport2_ports.py`'s pinned `CATEGORY_TOTAL`
(351 → **352**).

⚠ Those six counts were wrong in review round 1 of the pre-push gate
(322 → 323, 330 → 331, 31 → 32, 667 → 668, 51 → 52, and `CATEGORY_TOTAL`
322 → 323): they were the
pre-rebase numbers, written while this branch sat on an older `dev`, and the
code edits were re-based without the prose following. Each one above is now
read back out of the shipped file — `README.md:7,9,153`,
`docs/MLCompanionContract.md:27`, `tests/test_altport2_ports.py:196` — with
the "before" side read out of `git show 8000158:<path>` (`8000158`, the `dev`
commit this branch starts from).

`test_name_registration_and_accessor` asserts that `ts_strike_20` is in
`Category["statistics"]`, that `df.ta.ts_strike_20` exists and that the
accessor and the direct call return the same Series under the same name.
