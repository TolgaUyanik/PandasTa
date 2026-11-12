# `ts_peaks_20` — measured

Issue #92 (TS-PEAKS-20), ported 2026-11-12 on branch `issue-92-ts-peaks-20`.
Column: **`TS_PEAKS_20_2`**, `pandas_ta/statistics/ts_peaks_20.py`.
**Status: Gates A–F cleared. SHIP.**
Gate E was run by issue-solver on the committed module after the porting
session (run `is92-ts_peaks_20-7852eb1c`, measured 2026-11-13): max \|ρ\|
**0.2453** vs `BB_Lower` (compute_all, n = 397,158), top-5 per-frame max
median **0.2345**, 0 of 89 frames at \|ρ\| ≥ 0.90 → **SHIP**, below the 0.76
ship line. The row is in `docs/gate_e_ledger.csv`; the numbers and the run's
real-data reachability counts are in the *Gate E* and *Gate C* sections below.
Nothing was struck and nothing removed.

Every number the **porting** session measured comes from one of exactly four
commands: `python docs/measure_ts_peaks_20.py` (its sections can be run one at
a time, e.g. `… gate_b`), `python -m pytest tests/test_ts_peaks_20.py -q`,
`python -m pytest -q` (the Gate F suite line and the then-owed ledger row) and
`python docs/gen_indicator_dictionary.py` (the ML form tag and the warm-up).
The **Gate E** numbers and the real-data counts in *Gate C* come from one more
run, which the porting session could not make: issue-solver's
`gate_e_overlap.py run --module pandas_ta.statistics.ts_peaks_20`, read out of
that run's `overlap_max.csv`, `top25.csv`, `perframe.csv` and `meta.json`.
Figures *quoted from outside* those runs are labelled where they appear, and
there are four: the screen's Gate E numbers
(`docs/issues/091-ts-peaks-20.md`, the owner's tracker), commit 22fe27b's CI
counts (`git show`), the `classify` line number in
`docs/gen_indicator_dictionary.py` (read, not run), and the Gate E
configuration quoted from `CLAUDE.md` (89 frames, 687 comparators, the
`r3-perframe-0.90` bands).
Nothing in this file was typed from expectation; where a number is *not*
measured, the line says so.

⚠ **Spearman figures and last-bit counts here are this machine's.** CI's
runner measured 0.648490 where this machine measures 0.651029 for
`ts_binent_20`, on the same Python/numpy/pandas/scipy; commit 22fe27b widened
that pin to `abs=0.01` and attributed the drift to the runner's CPU rather
than isolating the cause. That is why `tests/test_ts_peaks_20.py` pins
correlations with a tolerance (0.06–0.08) and pins the *relations* where a
count could drift.

Two kinds of claim appear here and they are not equally strong:

* **Gate D's and Gate A2/A3/A4's bit-equality is structural.** The column is
  a count of comparison outcomes. A strictly increasing transform of price
  leaves every `>` unchanged, so the scaled run executes identical
  comparisons and sums identical integers — there is no rounding for a libm
  to disagree about. Likewise the oracles differ in *spelling*, not in
  arithmetic: all three count the same booleans. So `1481/1481` and `581/581`
  here are not lucky, unlike the float-pipeline equality that
  `docs/TsPerment20Measured.md` had to defend.
* **The Spearman numbers are frame-dependent** and only ordinally meaningful:
  the column takes at most 7 values, so every correlation against it is a
  rank statistic over heavy ties.

## What it is

    peak[P]      = c[P] > c[P-1] and c[P] > c[P-2]
                   and c[P] > c[P+1] and c[P] > c[P+2]
    TS_PEAKS[T]  = count of peak[P] for P in T-17 .. T-2

At the default (`length=20`; the support 2 is fixed by the issue): how many of
a 20-close window's **16 candidate bars** are a local maximum with support 2.
The window reads closes `T-19 .. T` and the first value lands at bar 19.

An **integer, 0 … 6** — not a continuous feature. Four consequences, all
measured below, that a consumer is likely to get wrong:

* **The freshest bar it can COUNT is T-2** (§The confirmation lag). Bar T's
  close is read — the two newest closes enter as confirmation of older
  candidates — but neither can be counted.
* **A flat, a rising, a falling and a zigzag frame all read 0.0** (§Gate A1,
  §What it reads). The comparison is strict, so a plateau is not a peak.
* **Magnitude is invisible** (§What it reads). A +10, +50 and +1000 sigma
  spike at the same bar give a bit-identical column.
* **Price granularity is an input** (§Gate D). The same path on a coarse grid
  is Spearman 0.5667 against the unrounded one.

## Source, and what "tsfresh (MIT)" does and does not mean here

The issue's line is `number_peaks(x, n=2) on 20 closes; a peak counts once
confirmed 2 bars later`, sourced to tsfresh `feature_calculators` (MIT).
**tsfresh is not installed in this worktree** — `import
tsfresh.feature_extraction.feature_calculators` raises
`ModuleNotFoundError` (measured, §source; pinned by
`test_tsfresh_is_not_installed_here`) — and web access is not available to
this session, so the attribution is an attribution and **not an oracle**.
Anything tsfresh does that the issue's line does not state (how it treats a
series shorter than `2n + 1`, whether it drops NaNs rather than refusing,
whether it returns a count or a share) is **unverified here**.

What IS independently checkable is the DEFINITION, and §Gate A checks it three
ways: the `np.roll` spelling of `number_peaks` run window by window, an
independent plain-Python scalar loop, and eight hand-derived windows.

The one reading of `n = 2` that matters: it means the loop
`for i in range(1, n + 1)` over BOTH sides, so a candidate must beat the
closes at ±1 **and** ±2 — four comparisons, not two. The issue's own
prototype spells exactly those four (next section), which is independent
evidence for that reading; §A5 prices the two alternatives.

## ⚠ The port is the screen's column ON CLEAN DATA — and that is not a Gate E

The screen prototype (`docs/issues/screen/ind_screen.py`, candidate
`ts_peaks_20`, local to the owner's machine) is:

    x = c.shift(2)                                       # candidate peak bar
    pk = (x > c.shift(3)) & (x > c.shift(4)) & (x > c.shift(1)) & (x > c)
    return pk.astype(float).rolling(16).sum().where(c.shift(19).notna())

Those are the four comparisons of `number_peaks(n=2)`, the 16 candidates of a
20-close window, and the same bar-19 warm-up. Measured, port against the
retyped prototype and against the owner's own registry entry
(`REG["ts_peaks_20"]["fn"]`, imported from the gitignored tree):

| frame | shared bars | bit-equal | NaN masks agree |
|---|---|---|---|
| walk | 1,481 | **1481/1481** | yes |
| tick-rounded | 1,481 | **1481/1481** | yes |
| coarse-grid | 1,481 | **1481/1481** | yes |
| two-point | 1,481 | **1481/1481** | yes |

So this port is the **opposite case** to issue #91's `ts_perment_20`, where
the prototype was a four-pattern sum and the port deliberately differed.

⚠ **Those four frames are clean, and the two functions are not the same off
clean data.** The prototype's comparisons are `False` at a NaN and its
`rolling(16).sum()` still emits a number, so it UNDERCOUNTS exactly where this
port refuses (§Guards). Measured, one NaN planted at bar 200 of a 400-bar
walk: the port is NaN where the prototype emits a number on **19** bars
(200 … 218 — the prototype's own `.where(c.shift(19).notna())` masks the
20th), and on the 361 bars where both fire they agree **361/361**. How often
the guard fires on real data is now answered by Gate E's counts: the run's
1,691 NaN bars are exactly 19 × 89, the warm-up (see *Gate C*), so the
divergence above did not occur on the 89 BIST frames.

**The screen's Gate E numbers still are not this module's receipt** — but the
port's own run landed on the same figures. The issue quotes max \|ρ\|
**0.2453** vs `BB_Lower` (n = 397,158, top-5 per-frame max median 0.2345) from
run `screen_20261024`, taken by the Gate E harness on the *prototype module*
against that date's comparator snapshot. Issue-solver's run on
`pandas_ta.statistics.ts_peaks_20` (`is92-ts_peaks_20-7852eb1c`) reports
0.24525200672691871 vs `BB_Lower`, n = 397,158, per-frame max median
0.23452801812896362 — the screen's numbers to every digit it printed. The
agreement is a *result* of the two runs, not an assumption either made; both
used 89 frames and 329 + 358 comparators, and whether anything else in the
snapshot moved between 2026-10-24 and 2026-11-13 is not something this
repository can see.
`test_the_ledger_row_is_this_modules_gate_e_run` now pins the recorded row
against the module on disk instead of asserting the row is absent.

## Gate A — correctness

### A1. Hand-derived windows

Eight windows whose answer is countable by hand (`gate_a`, and
`test_hand_derived_windows`):

| window (length) | peak positions | module |
|---|---|---|
| 20 identical closes | — | **0.0** |
| 20 strictly rising closes | — | 0.0 |
| 20 strictly falling closes | — | 0.0 |
| zigzag 100/101 × 20 | — | **0.0** |
| `[1,1,2]×6 + [1,1]` (the witness) | 2, 5, 8, 11, 14, 17 | **6.0** |
| `[1,2,5,2,1]` (length 5) | 2 | 1.0 |
| `[1,2,3,4,5]` (length 5) | — | 0.0 |
| `[1,2,9,2,1,2,9,2,1]` (length 9) | 2, 6 | 2.0 |

Two of those are the cases a reader gets wrong. A **plateau is not a peak**
(the comparison is strict): `[1]*8 + [5,5] + [1]*10` reads 0.0, and the same
window with the second 5 lowered to a 4 reads 1.0. And a **zigzag reads 0.0**,
because support 2 requires beating the close *two* bars away, which a
two-value alternation never does.

### A2. The screen prototype

See the previous section: bit-equal on 1,481 of 1,481 bars of four **clean**
frames, against both the retyped copy and the owner's registry entry — and off
clean data the two part company, measured in that same section.

### A3. `number_peaks` spelled with `np.roll`, window by window

The published spelling, sharing no code with the module:

    x_reduced = x[n:-n]
    res = None
    for i in range(1, n + 1):
        first = x_reduced > roll(x, i)[n:-n]
        res = first if res is None else res & first
        res &= x_reduced > roll(x, -i)[n:-n]
    return sum(res)

`np.roll` wraps, and the wrap is pinned never to reach the kept slice: over
every (candidate j, distance i) pair of a 20-close window, both `j - i` and
`j + i` stay inside `[0, 20)` — the offending-triple list is **empty**
(measured, §source; `test_np_rolls_wrap_never_reaches_the_kept_slice`).

Bit-equal to the module on **581 of 581** fired bars of each of four 600-bar
frames (walk, tick-rounded, coarse-grid, two-point), max \|diff\| 0.0, NaN
masks agreeing.

### A4. An independent plain-Python scalar loop

`all(w[j] > w[j+d] for d in (-2,-1,1,2))` per window, in Python scalars:
bit-equal on **581 of 581** bars of each of walk, tick-rounded and
coarse-grid.

Both oracles are also checked on a hand window where several candidates tie
with a neighbour — the case where a `>=` slip would show
(`test_the_oracles_agree_on_a_window_with_ties`): all three read 2.

### A5. The open readings, decided and priced

Spearman of the port against the column the *rejected* reading would give,
over 1,481 shared bars of a 1,500-bar frame (`gate_a`, A5):

| kept | rejected | walk | tick-rounded | coarse-grid |
|---|---|---|---|---|
| support on both sides at 1 **and** 2 | only the closes 2 away | 0.767425 | 0.750979 | 0.607045 |
| support 2 | support 1 (neighbours only) | 0.115928 | 0.348537 | 0.456213 |
| strict `>` | `>=` (a plateau is a peak) | **bit-equal, 1481/1481** | **bit-equal, 1481/1481** | **−0.098358** |
| window = 20 closes (16 candidates) | 20 candidates (24 closes) | 0.791649 | 0.802062 | 0.875618 |
| raw count (`np.sum`) | the share of 16 | **1.000000** | **1.000000** | **1.000000** |
| peaks of close | peaks of `-close` (troughs) | 0.288630 | 0.289679 | 0.140968 |
| the closes | the return series, same 16 positions | 0.096399 | 0.187320 | 0.259749 |
| the 2-bar confirmation | no confirmation, same 16 positions | 0.000035 | 0.028300 | 0.225866 |

Notes on three rows:

* **The share is an exact rescaling.** `count / 16` is Spearman 1.000000
  (printed to every digit by `gate_a`: **0.9999999999999999** on the walk,
  exactly **1.0** on the tick-rounded and coarse-grid frames — the rank
  correlation's own last bit, not the column's), and the ratio is exactly
  1/16 bar by bar, asserted. So it is the one open reading a rank miner
  cannot see; the raw count ships because that is what `np.sum` returns.
* **`>` vs `>=` is free on a continuous path and decisive on a coarse one.**
  Share of candidates tied with a neighbour within ±2, measured per frame:
  coarse-grid **0.517380** (774 of 1,496), tick-rounded 0.008021 (12 of
  1,496), and **0.000000** on walk, heavy-tailed, mean-reverting, trending
  and two-point. On the coarse grid the `>=` reading is an unrelated column
  (−0.098358, 8 distinct values against the port's 5).
* **Dropping the confirmation gives a different feature entirely** (0.000035
  on the walk): counting candidates that merely top their two predecessors,
  over the SAME 16 positions and the same warm-up, takes 15 distinct values
  and correlates with the confirmed count not at all. The confirmation is the
  definition, not a lag someone added.
  ⚠ That variant is **not** a same-bar column: it keeps the candidate
  positions, so the newest candidate is still bar T-2 and today's close is
  never counted — bar T still produces a value, it just cannot contain
  itself. What the row prices is the confirmation at a FIXED lag, which is
  the comparison worth making; the genuine same-bar column (candidates
  shifted to bars T-15 … T) was **not** measured.

### A6. The ceiling is 6, and it is attained

Two peaks cannot be closer than 3 bars: of two candidates 1 or 2 apart, each
would have to be strictly above the other. So the count is bounded by the
largest pairwise-3-apart subset of the 16 candidate positions. Enumerated
over **all 65,536 subsets** (`2**16`), that maximum is **6**, and exactly
**one** subset attains it — counted in the same enumeration, not argued:
window positions **(2, 5, 8, 11, 14, 17)** — and the 20-close witness
`[1,1,2]×6 + [1,1]` reads exactly **6.0**, pinned as a constant in the test
module.

The premise is measured too, not just argued: over **200,000** random
orderings of 20 distinct closes (20,000 in the test, for runtime) every pair
of peaks is at least 3 apart, the counts seen are `{0,1,2,3,4,5,6}` and the
maximum is 6.

So the column has **7 possible values**, and that is its main weakness as a
feature: a rank statistic over it carries heavy ties by construction.

## The confirmation lag

A peak at bar P is countable only once closes P+1 and P+2 exist, so the newest
candidate of the window ending at bar T is bar **T-2**. Measured
(`test_the_newest_candidate_is_two_bars_old`): planting a spike at the LAST
bar of a 400-bar frame leaves the column **bit-identical**; planting it two
bars earlier moves the last bar. This is the issue's "a peak counts once
confirmed 2 bars later" and it is in the source definition — it is not a
look-ahead-avoidance patch, and it cannot be removed without changing the
column (0.000035, §A5).

## Gate B — causality, by mutant

Five mutants, each `importlib`-read from the shipped file, one line replaced,
`exec`'d in memory, over two mechanisms:

| id | mutation |
|---|---|
| `back_date_two` | the write index back-dated 2 bars |
| `back_date_full` | the write index back-dated `length - 1` bars |
| `forward_flag` | the flag array rolled one candidate into the future |
| `rolled_window` | the flag array rolled `length // 2` candidates forward |
| `forward_leg` | both support legs ahead read one bar too far (p+2, p+3) |

The blind sweep: 37 offsets, J = 40 … 1480 step 40; at each one every close
from bar J on is replaced by a second independent frame's, and a **hit** means
some bar *strictly before* J moved (value or NaN). Caught offsets, out of 37:

| | walk | tick-rounded | heavy-tailed |
|---|---|---|---|
| **the real module** | **0** | **0** | **0** |
| `back_date_two` | 11 | 16 | 11 |
| `back_date_full` | 37 | 37 | 36 |
| `forward_flag` | 2 | 5 | 2 |
| `rolled_window` | 35 | 36 | 31 |
| `forward_leg` | 1 | 4 | 1 |

Same five mutants at non-default lengths on the walk (37 offsets each; the
real module leaks **0/37** at `length` 10, 60 and 5, with the first value at
bars 9, 59 and 4 respectively):

| | length 10 | length 60 | length 5 |
|---|---|---|---|
| `back_date_two` | 11 | 11 | 11 |
| `back_date_full` | 33 | 37 | 15 |
| `forward_flag` | 2 | 2 | 2 |
| `rolled_window` | 18 | 36 | 11 |
| `forward_leg` | 1 | 1 | 1 |

Every mutant is verified **live** (its column differs from the real one) in
each configuration, so a 1/37 row is a weak detector and not a dead mutation.

### Why the blind sweep is weak here, measured

The peak flag is sparse: **207 of 1,496** candidates on the walk (0.138369),
**223** tick-rounded (0.149064), **208** heavy-tailed (0.139037). A tail
perturbation that flips no flag is invisible to a counting column.

For `forward_flag` the mechanism is exact rather than narrated. Bar T of that
mutant reads the candidates at bars T-16 … T-1 instead of T-17 … T-2, so at
offset J the only prefix bar that can move is J-1, and the only candidate of
*its* window that reads the perturbed close J is the one at bar **J-2** (flag
index J-4). Measured: the set of caught offsets **equals** the set of offsets
where that single flag flips, on all three frames —

| frame | caught | flag flips at |
|---|---|---|
| walk | {280, 680} | {280, 680} |
| tick-rounded | {160, 880, 1000, 1120, 1280} | {160, 880, 1000, 1120, 1280} |
| heavy-tailed | {40, 680} | {40, 680} |

(`test_a_missed_mutant_offset_is_exactly_an_unflipped_flag` asserts the set
equality, so this explanation fails loudly if it stops being true.)

### The designed probe — which is what actually carries Gate B

Because the sweep is blunt, the gate does not rest on it. The probe targets
the one close each mutant reads illegally: take a bar `p` that **is** a peak,
lift the close at `p + k` above every close in the frame, and look at bar
`p + k - 1` — strictly before the perturbation. Over the first 50 peaks of a
1,500-bar walk:

| mutant | k | real module leaked | mutant caught |
|---|---|---|---|
| `forward_flag` | 2 | **0** | **50 of 50** |
| `forward_leg` | 3 | **0** | **41 of 50** |

The 9 misses are accounted for exactly, not waved at: all 9 are peaks that
the mutant's **own** flag already reads as false (it compares `p` against
`p+2` and `p+3`, so a real peak need not be one of its peaks), and then the
lift flips nothing. `41 + 9 = 50` is asserted, as is `real leaked == 0`; the
41 itself is banded 35–45 in the test, because WHICH peaks the mutant's own
flag rejects depends on the generated frame's last bits.

Also pinned: `offset=±2` is exactly `shift(±2)`; and
`test_prefix_truncation_alone_would_not_have_proved_this` shows the weaker
check the gate rejects — truncating the frame leaves every surviving bar
unchanged for the module **and** for the `back_date_two` mutant.

## Gate C — reachability

**Real data, from the Gate E run** (`is92-ts_peaks_20-7852eb1c`, 89 ALTPORT-1
BIST frames, 398,849 pooled bars):

| column | non-NaN | non-zero | degenerate frames |
|---|---|---|---|
| `TS_PEAKS_20_2` | **397,158** of 398,849 | **372,473** of 398,849 | **0** |

So the single shipped column fires on real data and is not constant there:
`0 < 372,473 < 398,849`, and the harness's `n_degenerate` is 0.

Two readings of those counts:

* the **1,691 NaN bars are exactly 19 × 89** — the warm-up, one frame's worth
  each. Nothing beyond the warm-up was masked, so the §Guards NaN path did not
  fire on these frames (the harness reports no per-frame NaN breakdown; this is
  the arithmetic, which also implies every frame is at least 20 bars long).
* **24,685 fired bars read 0** (6.22% of the fired bars): a window with no
  confirmed peak at all. On the synthetic frames below that share runs from
  0.34% (walk) to 98.9% (trending), so the real frames sit near the choppy end.

Measured over seven 1,500-bar synthetic frames (`gate_c_d`):

| frame | fires | distinct | min | max | median | mean | histogram |
|---|---|---|---|---|---|---|---|
| walk | 1481/1500 | 6 | 0 | 5 | 2.0 | 2.2039 | {0: 5, 1: 266, 2: 702, 3: 439, 4: 68, 5: 1} |
| tick-rounded | 1481/1500 | 6 | 0 | 5 | 2.0 | 2.3788 | {0: 12, 1: 205, 2: 579, 3: 584, 4: 97, 5: 4} |
| coarse-grid | 1481/1500 | 5 | 0 | 4 | 2.0 | 1.5206 | {0: 211, 1: 526, 2: 520, 3: 210, 4: 14} |
| heavy-tailed | 1481/1500 | 6 | 0 | 5 | 2.0 | 2.2289 | {0: 19, 1: 297, 2: 599, 3: 463, 4: 98, 5: 5} |
| mean-reverting | 1481/1500 | 6 | 0 | 5 | 2.0 | 2.4159 | {0: 32, 1: 154, 2: 567, 3: 624, 4: 102, 5: 2} |
| two-point | 1481/1500 | 6 | 0 | 5 | 2.0 | 1.8400 | {0: 97, 1: 467, 2: 569, 3: 276, 4: 68, 5: 4} |
| trending | 1481/1500 | **2** | 0 | 1 | 0.0 | 0.0108 | {0: 1465, 1: 16} |

So `0 < 1481 < 1500` on every frame and the column is non-constant on all
seven, which is what Gate D's "a constant column cannot pass" asks. **The
ceiling 6 is reached by none of them** — it exists (§A6) but it is rare.

Degenerate frames, all 1,500 bars: flat, strictly rising, strictly falling
and 100/101 zigzag each fire 1,481 bars with **1 distinct value, 0.0**.

## Gate D — scale-free

The column counts comparison outcomes, so it is invariant to any strictly
increasing transform of price, not merely to a multiplication. Measured
bit-identical (max \|diff\| exactly 0.0, 1481 of 1481 fired bars, NaN masks
agreeing) for **every one of the 42 combinations** of seven frames × {×8,
×64, ×1024, ×10, ×3.7, ×0.1}; and at non-default lengths on the walk under
×8: length 5 (1496/1496), 10 (1491/1491), 60 (1441/1441), 250 (1251/1251).

Beyond a scale, on the walk (one frame, which is what was run): `log`,
`sqrt`, `x**3` and `+1000` are all bit-identical, 1481/1481.

**Where the invariance stops.** The comparison is strict, so a transform that
rounds two distinct closes onto the same double would *destroy* a peak —
shown on a hand window rather than hoped about: `[1]*8 + [5,4] + [1]*10`
reads 1.0 and collapsing the 4 onto the 5 reads 0.0
(`test_a_collapse_would_destroy_a_peak`). On the seven frames measured no
scaling creates a new adjacent tie (0 new ties under each of ×8, ×1024, ×3.7,
×0.1; distinct closes: 1500/1500 on walk, heavy-tailed, mean-reverting,
trending and two-point, 1266/1500 tick-rounded, 79/1500 coarse-grid). That is
a measurement, not a guarantee.

Two transforms that are **not** strictly increasing maps of price and do move
the column:

* a **drift**, `× exp(0.004 · t)`: Spearman **0.406613** (722 of 1,481 bars
  still bit-equal);
* **rounding to a coarser grid**: the same path on a 1-decimal grid is
  Spearman **0.566696** against the unrounded one.

Price granularity is therefore an input to this column, and "scale-free" must
not be read as "tick-size-free".

## Gate E — attribution

**Run by issue-solver on the committed module, 2026-11-13.** Verdict
**SHIP** — nothing struck, nothing removed.

`gate_e_overlap.py run --module pandas_ta.statistics.ts_peaks_20` from
`../Backtesting/Backtesting`, outputs `is92-ts_peaks_20-7852eb1c`:
89 frozen ALTPORT-1 BIST frames, 398,849 pooled bars, 329 + 358 = 687
comparators, bands `r3-perframe-0.90`, canary bit-equal on AKBNK.IS, BIENY.IS,
AGHOL.IS, SASA.IS; pandas 2.3.3 / numpy 1.26.4; module sha1
`b571ed64b6a0356e9dd29269f0019478ad4fdae7`, tree sha1
`2a9dbc41ebb6c96425e59254bff9ced1fc819a97`; default parameters (`kwargs {}`),
nothing excluded.

| column | max \|ρ\| | against | set | n | per-frame max median | frames ≥ 0.90 | verdict |
|---|---|---|---|---|---|---|---|
| `TS_PEAKS_20_2` | **0.24525200672691871** | `BB_Lower` | compute_all | 397,158 | **0.23452801812896362** (`BB_Lower`, 89 frames) | **0 of 89** (0.0%) | **SHIP** |

Against each comparator set separately: `compute_all` 0.2453 vs `BB_Lower`
(n = 397,158); the `ml_features` `1d` manifest 0.17920404059782385 vs
`Pct_Up_Days_63` (n = 396,179). Both bands agree: pooled-only would also read
SHIP, and 0.2453 is below the 0.76 ship line by a wide margin — the nearest
band edge, DISCLOSE, is more than 3× this value.

**The top of the table is a plateau, so "vs `BB_Lower`" is close to
arbitrary.** The 25 strongest comparators span 0.24164 … 0.24525 — a range of
0.0036 — and they are nearly all price levels or smoothers: `BB_Lower`
0.24525, `LINREG_LOWER_2` 0.24319, `PSAR` 0.24302, `HWC_LOWER` 0.24287,
`donchian_DCL_20_20` and `SWING_LOW` 0.24276 (equal to the digit), `HWC_MID`
and `hwma` 0.24259, then `ROLLING_LOW_20`, `LINREG_LOWER_1`, `PREV_MONTH_LOW`,
`HWC_UPPER`, `PREV_WEEK_LOW`/`WEEK_LOW`, `pwma`, `LINREG_VALUE`, `ATR_LOWER`,
`trima`, `swma`, `sinwma`, `dema`, `SMA_14`, `hma`, `quantile`, `SMA_10`. A
count of local peaks correlates at \|ρ\| ≈ 0.242–0.245 with *any* of those
level columns and with none of them more; that is the shape of a weak shared
dependence on where price sits, not a restatement of one comparator.

Per-frame, over the top-5 pooled comparators (89 frames each): medians
0.2345 (`BB_Lower`), 0.2276 (`donchian_DCL_20_20`), 0.2271 (`HWC_LOWER`),
0.2250 (`PSAR`), 0.2221 (`LINREG_LOWER_2`); the single worst frame-comparator
pair is \|ρ\| **0.41549** and the mildest **0.00584**, both `BB_Lower`. No frame
reaches either the 0.90 strike line or the 0.80 disclosure line
(`pct_frames_ge_080` is 0.0 for all five).

Two figures from before the run, kept because they were written before it and
can now be scored:

* the issue's screen measured the **prototype** at max \|ρ\| 0.2453 vs
  `BB_Lower` (n = 397,158), next comparators `LINREG_LOWER_2` 0.2432 and
  `PSAR` 0.2430, top-5 per-frame max median 0.2345 → SHIP. The port's own run
  reproduces all five of those figures to the digits the issue printed, with
  the same three comparators in the same order (§A2);
* a **pre-check on one synthetic walk**, not Gate E (`meaning`): Spearman
  against fork neighbours computed on the same 1,500-bar walk —
  `chop` 0.293930, `ts_perment_20` 0.251457, `rsi` −0.149472,
  `entropy` −0.129591, `psl` −0.112006, `lean_hurst_100` −0.095211,
  `ts_c3_20` 0.048246, `ts_binent_20` −0.006100. Max \|ρ\| **0.2939**. It
  over-stated the real maximum by 0.049 and named a comparator (`chop`) that
  is not in the run's top 25; one synthetic frame and 8 comparators was never
  89 frames and 687.

Recorded in `docs/gate_e_ledger.csv` with
`python docs/gate_e_ledger.py record … --measured 2026-11-13`, which prints
`ts_peaks_20:TS_PEAKS_20_2 SHIP 0.2453 vs BB_Lower`; `record` re-checks that
the recorded tree is byte-identical to the one the harness imported, that the
parameters are the defaults, the universe the 89 frames, the comparator set
687 and the canary bit-equal.

## Gate F — suites

This repository, in the porting session:

* `python -m pytest tests/test_ts_peaks_20.py -q` → **192 passed**.
* `python -m pytest -q` → **3 failed, 6,285 passed, 83 skipped** (132.57 s on
  the last of four runs in that session; the three earlier ones, taken while
  this module had 184 and then 185 tests, reported the same three failures
  with 6,277/83 and 6,278/83).
  The three failures were the two `CLAUDE.md` *Known breaks*
  (`test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`, and
  `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`,
  which needs the sibling `../AlternativeRepos` checkout and is deselected in
  CI) plus the then-owed Gate E row, which reported exactly
  `['mtd_ret', 'ts_peaks_20']`.

And in this receipt session, after recording the row and rewriting this file's
Gate E and Gate C sections and the two ledger tests:

* `python -m pytest -q` → **3 failed, 6,293 passed, 83 skipped** (134.98 s,
  and 133.88 s on a second run after the last doc edits — same counts).
  The same two *Known breaks*, and
  `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` now
  reports exactly `['mtd_ret']` — `ts_peaks_20` has left that list, and
  `mtd_ret` is #206's, owed on `dev` and not this branch's to pay.
  The 8 new passes (6,285 → 6,293) are accounted for: **+1** in
  `tests/test_ts_peaks_20.py` (192 → 193 — the one "the ledger carries no
  `TS_PEAKS` row" assertion replaced by two that pin the row that is now
  there) and **+7** in `tests/test_gate_e_ledger.py`, which parametrises seven
  checks per ledger row and now collects them for
  `ts_peaks_20:TS_PEAKS_20_2`: `test_row_names_the_module_that_defines_the_indicator`,
  `test_row_still_describes_its_module`, `test_row_output_has_not_moved`,
  `test_verdict_follows_the_bands`,
  `test_struck_rows_carry_the_waiver_for_this_exact_measurement`,
  `test_ledger_columns_are_the_default_output` and
  `test_every_column_fires_on_real_data` (measured with
  `pytest tests/test_gate_e_ledger.py --co -k ts_peaks`, which collects those
  seven plus `test_every_new_indicator_has_gate_b_and_d_tests[ts_peaks_20]` —
  the eighth comes from `Category`, not the ledger, so it ran before the row
  too). So the row did not merely get written: four of those seven re-derive
  the module's sha1, its output fingerprint, its column set and the verdict
  band from this tree and would fail if the recorded run described different
  code.

The parent repo's suite is the launcher's to run, in a clean worktree.

## What the column reads

Median and spread over 1,500-bar frames (`meaning`):

| frame | median | mean | p05 | p95 | zeros |
|---|---|---|---|---|---|
| walk | 2.0 | 2.2039 | 1.0 | 3.0 | 5/1481 |
| tick-rounded | 2.0 | 2.3788 | 1.0 | 4.0 | 12/1481 |
| coarse-grid | 2.0 | 1.5206 | 0.0 | 3.0 | 211/1481 |
| heavy-tailed | 2.0 | 2.2289 | 1.0 | 4.0 | 19/1481 |
| mean-reverting | 2.0 | 2.4159 | 1.0 | 4.0 | 32/1481 |
| two-point | 2.0 | 1.8400 | 0.0 | 3.0 | 97/1481 |
| **trending** | **0.0** | 0.0108 | 0.0 | 0.0 | **1465/1481** |

Read that last row with the degenerate frames above: a strongly trending frame
and a **dead** one are nearly the same column here, 0 almost everywhere. This
is a *path-choppiness* feature, not a trend or volatility one.

**It cannot see magnitude.** Planting a +10, a +50 and a +1000 sigma return at
bar 700 of a walk moves **16** fired bars, and the three resulting columns are
**bit-identical** to each other (`test_the_column_cannot_see_magnitude`). All
three spikes put that close above its neighbours, and the count is all the
column reads.

**It counts peaks, not troughs.** The mirrored path (`-close`) is Spearman
0.288630 against the port on a walk, 0.289679 tick-rounded, 0.140968 on a
coarse grid. A consumer that wants both sides needs a second column; this one
is asymmetric by construction, as `number_peaks` is.

## Guards and edges

Measured on a 400-bar walk (`guards`):

* **19 closes at length 20 → `None`**, not a frame of NaNs (`verify_series`);
  4 closes at `length=5` likewise.
* **Exactly 20 closes** → fires once, at bar 19.
* **Warm-up** is `length - 1`: 19 NaNs, first value at bar 19.
* **`length` below 5 falls back to 20** — `None`, 0, 1, 2, 3, 4, −5 and 4.9
  all give `TS_PEAKS_20_2`, because a four-close window holds no candidate at
  all. `5` and `5.9` give `TS_PEAKS_5_2`, 21 gives `TS_PEAKS_21_2`.
* **At `length=5`** the column is exactly `{0.0, 1.0}` (one candidate a
  window), 396 fires of 400.
* **A window is emptied iff it holds a non-finite close**, which for an
  INTERIOR close — bar `length - 1` … `n - length` — is exactly `length` = 20
  bars: a NaN, `+inf` or `-inf` at bar 200 of a 400-bar frame invalidates the
  5 candidates it sits in, a window holds 16, and bars **200 … 219** go NaN
  and nothing else does. Nearer either end the warm-up or the end of the frame
  swallows part of the span, so FEWER bars are emptied — measured on the same
  frame: bar 0 → 1 bar, bar 2 → 3, bar 5 → 6, bar 19 → 20, bar 380 → 20,
  bar 397 → 3, bar 399 → 1. The column refuses rather than reading the NaN as
  "not a peak", which would undercount silently — which is what the screen
  prototype does (§The port is the screen's column on clean data).
* **A zero, negative or subnormal close is NOT rejected** (0.0, −5.0, 1e-310
  at bar 200 all leave 381 of 400 bars firing, bar 200 included): nothing here
  takes a ratio or a logarithm, unlike `ts_binent_20` / `ts_c3_20`.
* `fillna=0` leaves 0 NaNs. Every value is integer-valued in a float Series,
  asserted, so a consumer may cast it.

Wiring (touch points 2–4): `ts_peaks_20` is in `Category["statistics"]`,
`df.ta.ts_peaks_20()` returns `TS_PEAKS_20_2` and equals the function call,
`df.ta.ts_peaks_20(length=40)` renames to `TS_PEAKS_40_2`, `length`/`offset`
are forwarded, and `df.ta.strategy(Strategy(ta=[{"kind": "ts_peaks_20"}]))`
emits the column. `docs/IndicatorDictionary.md` tags it **`ORD`** with warm-up
19 (both read out of the regenerated file) — `classify` in
`docs/gen_indicator_dictionary.py:147` tags a column `ordinal` when its probe
observes at most 12 distinct values and all of them are integers, which this
count is. The observed cardinality itself is **not** recorded in the generated
file, so this receipt does not quote one. `ORD` is right for a coarse integer
count, and it is why `docs/MLCompanionContract.md`'s `ORD` tally moves 51 → 52
rather than its `SF` one.

## Cost

Best of three runs, one machine, with `tracemalloc` (`cost`):

| n | time | traced peak |
|---|---|---|
| 10,000 | 1 ms | 0.4 MB |
| 100,000 | 5–6 ms | 3.0 MB |
| 400,000 | **22–24 ms** | **11.7 MB** |

`length` is a caller parameter, so the peak must not grow with it. Measured at
n = 400,000:

| length | time | traced peak |
|---|---|---|
| 20 | 22–24 ms | 11.7 MB |
| 60 | 30–35 ms | 11.7 MB |
| 250 | 65–66 ms | **11.7 MB** |

The times are bands over the four `cost` runs made in this session on one
machine, not single readings: a best-of-three wall time is the one number here
that does not reproduce to the digit, and the memory column — which is what
this section exists for — reproduced exactly in every run. The length-20 row
is a second timing of the n = 400,000 row of the table above, which is why it
carries the same band.

That is flat because both row reductions write straight to `(rows,)`. It is
also the reason `bad` is spelled `windows.min(axis=1) < 0` and not the more
obvious `(windows < 0).any(axis=1)`. The two are equivalent **structurally** —
`min < 0` holds exactly when some element is `< 0`, for any numeric array —
and the run below is a smoke test of that, not its proof; what it does check
is that the smoke test had something to find: the flag array it runs on is the
module's own, over a 400,000-bar frame with a NaN and a `-inf` planted, and
all three reachable values are present (measured: **−1 × 10, 0 × 343,609,
1 × 56,377** of 399,996 candidates — an all-zero array, which an earlier
revision of this section used, could not have caught a difference at all).
The `any` form materialises a `(rows, length - 4)` bool array first. Measured
on those same windows at n = 400,000, agreeing on every window at both
lengths:

| spelling | peak at length 20 | peak at length 250 |
|---|---|---|
| `(windows < 0).any(axis=1)` | 6.8 MB | **98.7 MB** |
| `windows.min(axis=1) < 0` | **0.8 MB** | **0.8 MB** |

⚠ An earlier revision of this section said "memory is O(n) and the windows
themselves are a view" while the module still used the `any` spelling, which
traced 6.8 MB at the default length and 98.7 MB at `length=250` for that one
temporary. The sentence was written for the code someone meant to write. The
module was changed, not the sentence, and the table above is the measurement.
Because the two spellings are behaviourally identical, the suite cannot catch
a regression here: `test_the_nan_window_test_keeps_its_cheap_spelling` pins
the source line instead.

The remaining allocations are the `float64` copy of the closes, the `int64`
row sums and the `float64` output, each 3.2 MB at n = 400,000, plus the 0.4 MB
`int8` flag array and a few `bool` arrays of the same length.

## What a consumer must not do

* Do not read 0 as "quiet". 0 is the flat window, the monotone window, the
  zigzag window and most of a trending frame.
* Do not treat it as continuous. 7 values at length 20, and 6 of them in
  practice; bucketing or ranking it produces large tied groups.
* Do not expect same-bar reaction. The freshest candidate is 2 bars old.
* Do not pair it with a mirrored expectation: it counts maxima only.
* Do not assume tick size is irrelevant: coarser rounding is Spearman 0.5667
  against the same path unrounded.

## Reproducing

    python docs/measure_ts_peaks_20.py                 # every section
    python docs/measure_ts_peaks_20.py gate_a gate_b   # two of them
    python -m pytest tests/test_ts_peaks_20.py -q      # 192 tests

Sections: `source`, `gate_a`, `gate_b`, `designed`, `gate_c_d`, `meaning`,
`guards`, `cost`. Gate E is not among them: it needs the private Backtesting
engine and the 89 frozen BIST frames, neither of which is in this worktree.
