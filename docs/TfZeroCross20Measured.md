# TF-ZERO-CROSS-20 — `tf_zero_cross_20`, measured

PandasTa issue [#113](https://github.com/TolgaUyanik/PandasTa/issues/113).
Source: **TSFEL** (Fraunhofer Portugal AICOS, BSD-3-Clause),
`tsfel/feature_extraction/features.py` `zero_cross`.
Module: `pandas_ta/statistics/tf_zero_cross_20.py` · column
**`TFZEROCROSS_20`** (statistics, scale-free) · tests:
`tests/test_tf_zero_cross_20.py` · every number here is printed by
`python docs/measure_tf_zero_cross_20.py` — and the same figures come back
under `python docs/measure_tf_zero_cross_20_cpu.py --all` (§F2) — EXCEPT
§F1's test counts (pytest), §E's screen figures (issue #113, run
`screen_r2_20261024`, measured on the prototype and not on this module),
`CLAUDE.md`'s gate-table figures (the 687 comparators, the 89 frozen
ALTPORT-1 frames and the `r3-perframe-0.90` bands) and the `2213dc9` /
2026-11-11 date, which is read from `git log`.

`TFZEROCROSS_20` counts how many of the 19 adjacent pairs among the last 20
simple returns hold two returns of **different sign**, with `sign` the
three-valued `np.sign` the issue's line names. It is an integer on
`0 .. 19`.

**Three things a consumer must be told, and all three are measured below.**

1. ⚠ **It nearly restates `LEAN_MOMERSION_20`, which this fork already
   ships** (§L1, §L1b, §L1c). At `length` 21 it is an exact affine transform
   of momersion on any window with no flat bar — Spearman **−1.0000**, the
   identity holding on 1,479 of 1,479 bars of a walk and of a heavy-tailed
   frame. At the shipped default (20 returns, one pair fewer than
   momersion's window) Spearman runs **−0.9655 .. −0.9795** over the seven
   1,500-bar frames with no flat bar in them (the 0.01-tick `grid` frame, at
   0.40% flat returns, reads −0.9622). The 2026-10-24 screen behind the
   issue could not have seen this: `lean_momersion_20` landed 2026-11-11,
   eighteen days later (commit `2213dc9`, read from `git log`). **A further
   measurement is OWED from the Gate E run and carries a revert rule — see
   the Gate E section.**
2. ⚠ **A flat bar is its own sign** (§A4a, §A7). `np.sign(0.0)` is 0, so an
   unchanged close counts a change on the way in and on the way out. On a
   continuous frame that choice is invisible; on the same walk rounded to a
   0.5 grid (21.75% flat returns) it moves 1,418 of 1,480 bars by up to 10.
   Real daily data is a tick grid, so this is not an edge case there.
3. ⚠ **A level shift does not move the column**, so the usual Gate D
   anti-vacuity check does not work here (§D). What is measured instead is
   that the column is not constant: 13 to 15 distinct values on each of the
   nine varied frames, and all of `0 .. 19` reached pooled.

Gate E: **pending, run by issue-solver after this session.** The issue's
figure — max |ρ| 0.3498 vs `stdev`, n = 397,158, per-frame max median
0.3296, SHIP — is the 2026-10-24 screen's, measured on the prototype and not
on this module. Gate C's real-data limb is owed from the same run (§C1).

---

## Gate A — correctness

### §A — what the source says here, and what it does not

The whole of the source text available in this worktree is the one line
issue #113 quotes:

    features.py zero_cross: #diff(sign(x)) != 0

TSFEL is not installed, `docs/pine/` does not carry it, and web access is
unavailable (§A6 prints `import tsfel -> ImportError: No module named
'tsfel'`, and `docs/*tsfel* : []`).
`tests/test_tf_zero_cross_20.py::test_the_source_library_is_not_readable_here`
asserts both, so the limitation fails loudly if the environment changes.

So Gate A checks **the quantity that line names**, not TSFEL's code: the
number of adjacent pairs inside the window whose two `np.sign` values
differ. It is spelled three ways —

* the owner's screen prototype, `docs/issues/screen/ind_screen_r2.py:216-217`
  (§A1);
* a window-by-window Python retype of the line itself,
  `len(np.where(np.diff(np.sign(w)))[0])`, sharing no code with the module
  (§A3);
* the module's own prefix-sum spelling, which §Z also checks against a
  `(rows, length)` block form.

Anything TSFEL does that the line does not state — how it treats a NaN, for
instance — is **unverified here**. The 20 is the issue's own parameter and
the input is the simple return, which is the prototype's reading of "daily
returns".

### §A1 — the screen prototype

The prototype is

```python
@cand("tf_zero_cross_20", "sign changes of daily returns (20)", TF,
      "features.py zero_cross: #diff(sign(x)) != 0")
def _(o, h, l, c, v):
    return roll(ret(c), 20,
                lambda W: (np.diff(np.sign(W), axis=1) != 0)
                .sum(1).astype(float))
```

with `ret(c) = c / c.shift(1) - 1`. The module calls
`close.pct_change(fill_method=None)` instead; the two return series are
**bit-equal on all twelve frames**, so that is a spelling and not a
difference.

Agreement is reported as EXACT equality and never as a tolerance: the
arithmetic is an integer count, so a tolerance would hide a real difference
rather than absorb a rounding one.

| frame | bars both | differ | only module | only prototype |
|---|---|---|---|---|
| walk | 1480 | 0 | 0 | 1 |
| trend | 1480 | 0 | 0 | 1 |
| range-bound | 1480 | 0 | 0 | 1 |
| grid | 1480 | 0 | 0 | 1 |
| coarse-grid | 1480 | 0 | 0 | 1 |
| heavy-tailed | 1480 | 0 | 0 | 1 |
| jump | 1480 | 0 | 0 | 1 |
| persistent | 1480 | 0 | 0 | 1 |
| mean-reverting | 1480 | 0 | 0 | 1 |
| flat | 1480 | 0 | 0 | 1 |
| ramp (200 bars) | 180 | 0 | 0 | 1 |
| alternating | 1480 | 0 | 0 | 1 |
| **TOTAL** | **16460** | **0** | **0** | **12** |

**The one deliberate divergence** is the last column. `np.sign(NaN)` is NaN
and `NaN != 0` is True, so the prototype COUNTS a missing return's two
comparisons as sign changes; this module reports the window as missing,
which is the fork's convention. Every frame has at least one such window —
the one at bar `length - 1`, which holds `r[0]`, the return of the first
close, which no close precedes. What the prototype reads there against the
count over the 18 pairs of that window that are known:

| frame | prototype at bar 19 | the 18 known pairs |
|---|---|---|
| walk | 8 | 7 |
| grid | 9 | 8 |
| alternating | 19 | 18 |

i.e. exactly one spurious change, from the one unknown return. On real data
the same rule applies to every gap, which is the case that matters: a frame
with a missing or zero close would have the prototype reporting counts for
windows it cannot see.

### §A2 — the prototype at other lengths

Same comparison at `length` 2, 5, 20, 60 and 250, on the walk, the 0.01 grid
and the heavy-tailed frame. **0 differ** in all fifteen cells, over
1498 / 1495 / 1480 / 1440 / 1250 shared bars each.

### §A3 — TSFEL's line, window by window

`len(np.where(np.diff(np.sign(w)))[0])` in a Python loop over each window,
sharing no code with the module, with this port's gap rule: **0 differ on
16,460 bars** of the twelve frames, and the NaN masks are equal on all
twelve.

### §A4 — the readings this port did NOT take

**§A4a — a two-valued sign.** The alternative is `-1` below zero and `+1` at
or above it, so a flat bar belongs to the up camp instead of being its own.

| frame | zero returns | bars differing | max abs diff | Spearman |
|---|---|---|---|---|
| walk | 0 | 0 | 0 | 1.000000 |
| trend | 0 | 0 | 0 | 1.000000 |
| range-bound | 0 | 0 | 0 | 1.000000 |
| grid | 6 | 96 | 2 | 0.992566 |
| coarse-grid | 326 | 1418 | 10 | 0.617645 |
| heavy-tailed | 0 | 0 | 0 | 1.000000 |
| jump | 0 | 0 | 0 | 1.000000 |
| persistent | 0 | 0 | 0 | 1.000000 |
| mean-reverting | 0 | 0 | 0 | 1.000000 |

The three-valued form is the one the issue's line names (`np.sign`), and it
is kept. On a continuous frame the two are the same column bit for bit; the
choice is only visible where closes repeat, which is where real data lives.

**§A4b — `length` is 20 RETURNS, not 20 closes.** The issue says "daily
returns (20)" and the prototype windows `ret(c)`, so a value needs 21
closes. The 19-return reading is a different column: 727 of 1,480 shared
bars differ on the walk (Spearman 0.968399, max difference 1) and 726 on the
0.01 grid (0.974880).

**§A4c — the RAW count.** The source function returns the count, not a
share, so `TFZEROCROSS_20` does too. Dividing by `length - 1` is an exact
rescaling (Spearman 1.000000 on the walk and on the heavy-tailed frame), so
it is the one choice a rank miner cannot see.

### §A5 — the anchors: what a KNOWN process must read

A sign change between two independent continuous returns has probability
1/2, so 19 pairs centre on **9.5**. Over 4,000 disjoint windows of iid
normal returns: mean **9.5077**, sd 2.1991, median 10, min 2, max 17. ⚠ The
spread is the point: a single reading of 12 says very little.

| frame | median | mean | min | max |
|---|---|---|---|---|
| walk | 9.0 | 9.3230 | 3 | 15 |
| trend | 8.0 | 8.7095 | 2 | 16 |
| range-bound | 10.0 | 9.5804 | 3 | 16 |
| grid | 9.0 | 9.3182 | 3 | 16 |
| coarse-grid | 13.0 | 12.3568 | 6 | 19 |
| heavy-tailed | 10.0 | 9.7405 | 4 | 16 |
| jump | 9.0 | 8.7358 | 3 | 16 |
| persistent (AR φ = +0.6) | 6.0 | 6.0899 | 0 | 13 |
| mean-reverting (AR φ = −0.6) | 13.0 | 13.4182 | 7 | 19 |
| flat | 0.0 | 0.0000 | 0 | 0 |
| ramp | 0.0 | 0.0000 | 0 | 0 |
| alternating | 19.0 | 19.0000 | 19 | 19 |

The ordering the column exists for — mean-reverting above the walk above
persistent — holds, and both constructed ends are reached.

⚠ The **coarse-grid** row is a second ordering worth reading: a coarser
price grid pushes the column UP (median 13.0 against the walk's 9.0),
because flat bars manufacture changes. That is the three-valued sign, not
mean reversion.

### §A6 — is the source readable here?

    import tsfel -> ImportError: No module named 'tsfel'
    docs/*tsfel* : []

### §A7 — the flat return, which is the whole of the sign choice

Closes 100, 101, 101, 102, 103 … give returns NaN, +, 0, +, +. At `length`
2 the column reads

    [None, None, 1, 1, 0, 0, 0, 0]

— the pair (+, 0) and the pair (0, +) are each one change, so one unchanged
close adds two.

How often that happens, by grid, on the same 1,500-bar walk:

| frame | zero returns |
|---|---|
| walk | 0.00% of 1499 |
| grid (0.01 tick) | 0.40% |
| coarse-grid (0.5 tick) | 21.75% |
| flat | 100.00% |

⚠ Real BIST daily data is a tick grid, not a continuous walk. The live share
is owed from the Gate E run.

---

## Gate B — causality

Offsets swept: 25, 235, 445, 655, 865, 1075, 1285, 1495. At each one the
frame is split into two futures that agree **bit for bit** below the offset
and whose return AT the offset has the opposite sign (one rises every bar,
one alternates starting down; only the return at the offset is guaranteed
opposite, since from the next bar on one is always up and the other
alternates). "Caught" means the prefix BELOW the perturbation moved.

⚠ **Why the futures are deterministic.** The fork's other ports sweep with
a seeded RANDOM pair. §B5 measures both and they agree at every usable
offset, so this is not a strengthening of what the suite checks; what it
buys is that the opposite sign at the offset is a GUARANTEE rather than
something a seed happened to produce, so "caught at every usable offset" is
a property of the construction and not of `default_rng(90_001 + j)`.

⚠ **An offset whose PREVIOUS return is flat is dropped** (column "usable").
With `r[j-1]` flat the pair `(r[j-1], r[j])` is a change in BOTH futures
whatever sign `r[j]` takes, so the two prefixes agree and the offset proves
nothing about either module. That is not hypothetical: on the 400-bar
0.5-grid frame the test module builds, two of its eight offsets are flat,
and with them in the sweep a mutant that does read ahead came back caught
on only 6 of 8. §B5 measures both halves of it.

| frame | usable | real module | tomorrow | sign rolled | centred | early write |
|---|---|---|---|---|---|---|
| walk | 8 | 0 | 8/8 live | 8/8 live | 8/8 live | 8/8 live |
| trend | 8 | 0 | 8/8 live | 8/8 live | 8/8 live | 8/8 live |
| range-bound | 8 | 0 | 8/8 live | 8/8 live | 8/8 live | 8/8 live |
| grid | 8 | 0 | 8/8 live | 8/8 live | 8/8 live | 8/8 live |
| coarse-grid | 8 | 0 | 8/8 live | 8/8 live | 8/8 live | 8/8 live |
| heavy-tailed | 8 | 0 | 8/8 live | 8/8 live | 8/8 live | 8/8 live |
| jump | 8 | 0 | 8/8 live | 8/8 live | 8/8 live | 8/8 live |
| persistent | 8 | 0 | 8/8 live | 8/8 live | 8/8 live | 8/8 live |
| mean-reverting | 8 | 0 | 8/8 live | 8/8 live | 8/8 live | 8/8 live |

The four mutants are the shipped file read off disk, one line replaced, and
`exec`'d in memory:

| mutant | the edit |
|---|---|
| tomorrow | `r = np.roll(close.pct_change(…).to_numpy(dtype=float), -1)` |
| sign rolled | `sign = np.roll(np.sign(np.where(finite, r, 0.0)), -1)` |
| centred | `sign = np.roll(np.sign(…), -(length // 2))` — the `bos` failure mode |
| early write | `out[length - 1:-1] = …` instead of `out[length:] = …` |

### §B2 — the mutant the blind sweep cannot see

The fifth mutant back-dates the GAP MASK:
`np.where(np.roll(n_finite == length, -1), count, np.nan)`. A back-dated gap
depends on no future VALUE, so on a frame with no gap the mutant is not even
live and the sweep reads 0 of 8 — measured `live=False, caught=0/8` on the
walk, the trend and the range-bound frame. It is caught by planting one NaN
close and reading where the gap lands:

| NaN close at | real: first gap | mutant: first gap |
|---|---|---|
| 200 | 200 | 199 |
| 600 | 600 | 599 |
| 1000 | 1000 | 999 |

### §B5 — the futures, and what the dropped offsets would have proved

The same four mutants swept with the RANDOM futures the fork's other ports
use (one future scaled by `1 + 3u`, the other by its reciprocal), beside the
deterministic pair, at both scales:

| frames | frame | usable | deterministic | random |
|---|---|---|---|---|
| 1,500-bar | walk / grid / coarse-grid | 8 | 8/8 on all four mutants | 8/8 on all four |
| 400-bar | walk / grid | 8 | 8/8 on all four | 8/8 on all four |
| 400-bar | coarse-grid | 6 | 6/6 on all four | 6/6 on all four |

So at a **usable** offset the two builders are equivalent on every cell
measured: the determinism is belt and braces, and the `_offsets` filter is
what the 6-of-8 failure was actually about. At the two **dropped** offsets
of the 400-bar 0.5-grid frame (131 and 395, `r[j-1] == 0.0` at each):

| mutant | deterministic | random |
|---|---|---|
| tomorrow | 0/2 | 0/2 |
| sign rolled | 0/2 | 0/2 |
| centred | **2/2** | 0/2 |
| early write | 0/2 | 0/2 |

A one-bar reader is invisible there to both, which is exactly why the
offset is dropped. The `centred` mutant reads `length // 2` bars ahead and
is still caught by the deterministic pair — the one place the two builders
part. `tests/test_tf_zero_cross_20.py::test_the_deterministic_futures_catch_a_wide_reader_at_a_dropped_offset`
sweeps exactly those offsets so that advantage is exercised by the suite
and not only here; it is NOT the reason the builder is deterministic
(that is the guarantee above), it is the one measured consequence.

### §B3 — prefix truncation

Truncating the frame at each swept offset leaves the column unchanged on all
twelve frames. ⚠ That is the WEAK check — it cannot see a value back-dated
inside the prefix, which is what §B2 is for.

### §B4 — one changed close moves only the windows that hold it

The check a prefix sum specifically has to pass is locality: its totals run
the length of the frame, so a bug there would move far-away bars. One close
multiplied at bar 200 and at bar 800 of a walk:

| change | bars moved | of them outside `at .. at + 20` |
|---|---|---|
| ×1.500 at 200 | 4 | 0 |
| ×0.667 at 200 | 0 | 0 |
| ×1.500 at 800 | 0 | 0 |
| ×0.667 at 800 | 21 | 0 |

(Two of those four rows move nothing at all: the column is a coarse integer,
and a 50% move of one close need not change any pair's SIGN.)

---

## Gate C — reachability

### §C1 — real data

⚠ **Owed.** It comes off the Gate E run, which issue-solver runs after this
session. No real frame is reachable from this worktree.

### §C2 — synthetic frames

| frame | bars | fires | distinct | min | median | max |
|---|---|---|---|---|---|---|
| walk | 1500 | 1480 | 13 | 3 | 9.0 | 15 |
| trend | 1500 | 1480 | 15 | 2 | 8.0 | 16 |
| range-bound | 1500 | 1480 | 14 | 3 | 10.0 | 16 |
| grid | 1500 | 1480 | 14 | 3 | 9.0 | 16 |
| coarse-grid | 1500 | 1480 | 14 | 6 | 13.0 | 19 |
| heavy-tailed | 1500 | 1480 | 13 | 4 | 10.0 | 16 |
| jump | 1500 | 1480 | 14 | 3 | 9.0 | 16 |
| persistent | 1500 | 1480 | 14 | 0 | 6.0 | 13 |
| mean-reverting | 1500 | 1480 | 13 | 7 | 13.0 | 19 |
| flat | 1500 | 1480 | 1 | 0 | 0.0 | 0 |
| ramp | 200 | 180 | 1 | 0 | 0.0 | 0 |
| alternating | 1500 | 1480 | 1 | 19 | 19.0 | 19 |

Warm-up: the first reading is at bar **20**, not 19 — 20 returns need 21
closes. Pooled over the twelve frames every one of the 20 reachable values
`0 .. 19` is observed, and nothing outside that range is.

---

## Gate D — scale-free

### Exact binary factors: bit-identical

×8, ×64, 2⁻⁴⁰, 2⁴⁰ and 2¹⁰⁰ on all twelve frames: **bit-identical in all 60
cells**. ×8 again at `length` 2, 5, 20, 60 and 250 on the walk:
bit-identical at all five.

### Inexact factors: ALSO bit-identical

This is stronger than the gate asks for, and it holds because only the SIGN
of a price ratio reaches the output. ×10, ×3.7, ×0.1 and ×1.0000001 on all
twelve frames: **0 bars differ in all 48 cells**. It is a measurement and
not a guarantee — a non-binary factor can round two closes to the same
double, which would turn a signed return flat; no frame here reaches that.

A monotone power map of the price cannot reorder two closes, and `1/price`
reverses every return, which leaves every DISAGREEMENT a disagreement:
`price**2`, `sqrt(price)` and `1/price` all differ on **0 of 1,480** bars of
the walk, the 0.01 grid and the heavy-tailed frame.

### ⚠ A level shift does NOT move it, and that is a property

`c + k > c' + k` exactly when `c > c'`, so adding a constant to the price
cannot change the sign of any return.

| shift | bars moved of 1480 | max abs diff | min close | closes < 0 |
|---|---|---|---|---|
| +10.0 | 0 | 0 | 48.09 | 0 of 1500 |
| +100.0 | 0 | 0 | 138.09 | 0 of 1500 |
| −50.0 | **74** | 2 | −11.91 | 970 of 1500 |
| −200.0 | 0 | 0 | −161.91 | 1500 of 1500 |
| −1000.0 | 0 | 0 | −961.91 | 1500 of 1500 |

Only the shift that makes the path **straddle** zero moves it. Where the two
closes of a pair have opposite signs the ratio's order flips; where they are
both negative it flips for EVERY pair at once, and flipping every sign
leaves every disagreement a disagreement — which is why −200.0 and −1000.0,
with every close negative, move nothing.

**So "a shift moves it" cannot stand in for "the column is live" here.**
What does: the column is not constant.

| frame | fires | distinct values |
|---|---|---|
| walk | 1480 of 1500 | 13 |
| trend | 1480 of 1500 | 15 |
| range-bound | 1480 of 1500 | 14 |
| grid | 1480 of 1500 | 14 |
| coarse-grid | 1480 of 1500 | 14 |
| heavy-tailed | 1480 of 1500 | 13 |
| jump | 1480 of 1500 | 14 |
| persistent | 1480 of 1500 | 14 |
| mean-reverting | 1480 of 1500 | 13 |
| flat | 1480 of 1500 | 1 |
| ramp | 180 of 200 | 1 |
| alternating | 1480 of 1500 | 1 |

`0 < fires < n` on every frame.

---

## Gate E — attribution

**Pending, run by issue-solver after this session.** When the run lands, its
row goes into `docs/gate_e_ledger.csv` and its numbers into this section;
`tests/test_tf_zero_cross_20.py::test_the_gate_e_row_is_owed_and_not_yet_recorded`
asserts the row is absent, which is the receipt session's cue.

What exists today is the **screen's figure, measured on the prototype and
not on this module** (issue #113): max |ρ| **0.3498** vs `stdev` over
n = 397,158, top-five per-frame max median 0.3296 → SHIP, then `LINREG_DEV`
0.3417 and `mad` 0.3367; run `screen_r2_20261024`, 89 ALTPORT-1 frames,
329 + 358 comparators, canary bit-equal. §A1 shows this module and the
prototype agree exactly wherever BOTH are defined — the prototype also reads
one bar per frame that this module reports as a gap — so the figure is
expected to carry over, and Gate E's statistic is a Spearman over the bars
where both fire. The launcher's run on THIS module is still the number that
decides.

⚠ **What the Gate E comparator set cannot see.** Its 687 comparators are the
engine's `compute_all` ∪ the `ml_features` manifest, not this fork's own
`Category` columns, so a SHIP verdict there says nothing about §L1's
−0.97 against `LEAN_MOMERSION_20`. The screen's stage-2 fork overlap, which
would see it, ran on 2026-10-24 and reported 0.2420 vs
`chop:CHOP_14_1_100` — eighteen days before `lean_momersion_20` landed, so
that number is about a fork that did not yet contain the overlapping
column.

**OWED from the Gate E run — with a rule, not a note.** The redundancy call
is the owner's, but "the owner's call" with no trigger is a call that never
gets made: the moment a SHIP row is recorded, every test here goes green
and the disclosure becomes prose. So the receipt session owes:

> Compute Spearman(`TFZEROCROSS_20`, `LEAN_MOMERSION_20`) pooled and its
> top-five per-frame median over the same 89 ALTPORT-1 frames the Gate E
> run uses, read it against the same `r3-perframe-0.90` band, record both
> numbers in this section, and **revert `tf_zero_cross_20` if it is
> STRUCK** (pooled |ρ| ≥ 0.90, or a per-frame median ≥ 0.90). The ledger
> has no field for a fork-internal overlap, so this section is where it
> lives.
>
> What the synthetic frames predict: STRUCK below roughly 5% flat returns,
> SHIP above roughly 20% (§L1c). The real flat-return share of BIST daily
> closes decides it, and it is not measurable from this worktree.

`tests/test_tf_zero_cross_20.py::test_the_overlap_measurement_is_still_owed_from_the_gate_e_run`
asserts this item is still here, so it cannot be dropped silently.

---

## Gate F — suites

### §F1 — this repo

`python -m pytest tests/test_tf_zero_cross_20.py -q` → **336 passed**, and
the same 336 under `python docs/measure_tf_zero_cross_20_cpu.py`, which
disables `AVX512F AVX512_SKX AVX2 FMA3` and refuses to run if the
environment edit did not take.

Full suite: **3 failed, 10,611 passed, 85 skipped**. The three are
`tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
(the known clean-checkout break, `CLAUDE.md` "Known breaks"),
`tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout; CI deselects it by name)
and
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
whose message names
`['arch_lm', 'diff2_acf1', 'edge', 'firstzero_ac', 'halflife', 'lumpiness',
'mtd_ret', 'tf_zero_cross_20']` — the owed row this commit ships with. CI
into `dev` sets `GATE_E_PENDING_OK=1` and skips the last.

### §F2 — which figures move between the two dispatches

**None of them.** `python docs/measure_tf_zero_cross_20.py` and
`python docs/measure_tf_zero_cross_20_cpu.py --all` print the same digest,

    DIGEST A1,A2,A3,A4,A5,A6,A7,B,C,D,G,L,W
    108bc7c39deb6b45b9c9115d98df5bbf2e7716a5

a sha1 over everything the deterministic sections printed. §Z is excluded
because it reports traced memory peaks, which are a property of the run.

That the digests match is a measurement, not a derivation from the
arithmetic. The column's own arithmetic is integer — a sign, a comparison
and two `int64` prefix sums — but the synthetic frames are built with
`np.exp` and `np.cumsum`, whose last bits ARE dispatched, so a close could
in principle have landed on a different tick.

---

## §G — guards

One close replaced at bar 200 of a 1,500-bar walk. A close of 0 breaks the
NEXT return, not its own (`0 / c[199] - 1` is `-1`, a number;
`c[201] / 0 - 1` is infinite), which is why the gap starts one bar later for
some values than for others.

| close[200] = | fires | gap bars | first gap | last gap | values moved | of them before 200 |
|---|---|---|---|---|---|---|
| NaN | 1459 | 21 | 200 | 220 | 0 | 0 |
| inf | 1460 | 20 | 200 | 219 | 1 | 0 |
| −inf | 1460 | 20 | 200 | 219 | 1 | 0 |
| 0.0 | 1460 | 20 | 201 | 220 | 0 | 0 |
| −100.0 | 1480 | 0 | — | — | 2 | 0 |
| 1e−310 | 1460 | 20 | 201 | 220 | 0 | 0 |
| ×1.5 | 1480 | 0 | — | — | 4 | 0 |

**A NEGATIVE close is a price here, not a gap** (row −100.0): nothing in
this module takes a logarithm, so the ratio exists and is read. That is a
deliberate difference from `ts_cross_mean_20`, which must drop a
non-positive close because it has no logarithm.

A subnormal close (1e−310) is a gap, but by overflow rather than by rule:
`c[201] / 1e-310` is infinite.

Nothing raises under `np.errstate(all="raise")` — on all twelve frames, and
on a frame with 0.0, NaN and inf planted at bars 200, 400 and 600, which
fires 1,419 of 1,500. The input Series is not mutated. The shortest input
that produces a value is `length + 1` closes (`length` closes returns
`None`), and a `length` below `MIN_LENGTH` = 2, or missing, falls back to
20.

---

## §L — what the column reads, and what it overlaps

### §L1 — the fork columns nearest to it

Spearman on 1,500-bar synthetic frames. ⚠ SYNTHETIC: the number that decides
ship or revert is the launcher's Gate E run on the 89 BIST frames.

The `flat?` column is the script's own, and it is what defines the band
below: `-` is a frame with no exactly-zero return, `flat` one with some.

| frame | flat? | LEAN_MOMERSION_20 | TS_CROSS_MEAN_20 | TFCENTROID_20 | STDEV_20 | MAD_20 | mean abs return |
|---|---|---|---|---|---|---|---|
| walk | − | −0.9699 | 0.2957 | 0.1087 | −0.2135 | −0.2281 | −0.0287 |
| trend | − | −0.9795 | 0.2770 | −0.0130 | −0.1579 | −0.1624 | −0.0858 |
| range-bound | − | −0.9655 | 0.1522 | −0.0895 | −0.3076 | −0.2967 | −0.1876 |
| grid | flat | −0.9622 | 0.2382 | 0.0149 | −0.2410 | −0.2310 | −0.0028 |
| coarse-grid | flat | −0.7586 | 0.2934 | −0.0042 | −0.4919 | −0.4836 | −0.2362 |
| heavy-tailed | − | −0.9701 | 0.1398 | −0.0185 | −0.2090 | −0.2051 | −0.1041 |
| jump | − | −0.9672 | 0.2227 | −0.0413 | −0.4157 | −0.3958 | −0.0969 |
| persistent | − | −0.9737 | 0.1495 | −0.0637 | −0.4121 | −0.4049 | −0.4762 |
| mean-reverting | − | −0.9789 | 0.3502 | 0.0063 | −0.1346 | −0.1427 | 0.3461 |

The script prints the band over the seven `-` rows itself: momersion
**−0.9655 .. −0.9795**. `grid` (−0.9622) and `coarse-grid` (−0.7586) have
flat bars and are NOT in it.

Everything except momersion is far from a restatement, and the two
comparators the screen named — `stdev` and `mad` — read −0.13 to −0.49 here,
consistent with the screen's 0.3498 / 0.3367 on real frames.

### §L1b — how close momersion is, exactly

`LEAN_MOMERSION_20` takes the sign of each return, pairs consecutive
returns, counts the pairs that AGREE (MC) and that OPPOSE (MRC) over
`length` pairs, and reports `100 * MC / (MC + MRC)`. With no flat bar in the
window every pair is signed, so `MC + MRC` is 20 and momersion is exactly

    100 * (20 - MRC) / 20

and MRC is this column at `length` 21 — the same window, since momersion's
20 pairs span 21 returns.

| frame | ρ vs momersion at length 20 | at length 21 | bars where `100*(20−count₂₁)/20` equals momersion |
|---|---|---|---|
| walk | −0.9699 | **−1.0000** | 1479 of 1479 |
| grid | −0.9622 | −0.9858 | 1368 of 1479 |
| coarse-grid | −0.7586 | −0.7834 | 23 of 1479 |
| heavy-tailed | −0.9701 | **−1.0000** | 1479 of 1479 |

### §L1c — what separates them is flat bars

The same walk rounded to a coarser and coarser tick:

| tick | zero returns | ρ vs momersion (length 20) | at length 21 |
|---|---|---|---|
| 0.001 | 0.07% | −0.9733 | −0.9968 |
| 0.01 | 0.40% | −0.9622 | −0.9858 |
| 0.05 | 2.27% | −0.9317 | −0.9539 |
| 0.1 | 4.40% | −0.9146 | −0.9371 |
| 0.25 | 11.47% | −0.8322 | −0.8602 |
| 0.5 | 21.75% | −0.7586 | −0.7834 |
| 1.0 | 37.63% | −0.6647 | −0.6800 |
| 2.0 | 63.04% | 0.0097 | 0.0042 |

⚠ Which row of that table real BIST daily data sits in is NOT measured here.
It comes off the Gate E run — the engine's comparator set does not contain
`LEAN_MOMERSION_20`, but the run's own frames would make the measurement
possible.

**What this means for a feature set.** Below about 5% flat returns the two
columns are one signal at two scales, and a miner given both double-weights
it. Above about 20% they are measurably different columns, and the
difference is exactly the treatment of flat bars (§A4a) — which is a real
property of the data, not noise. The owner's call.

### §L2 — blind to the size and the sign of the returns

Rebuilding the frame from the same return array scaled by a constant:
`×0.5`, `×2`, `×−1` and `×1e−6` each differ on **0 of 1,479** shared bars.
`×−1` flips every sign, which leaves every disagreement a disagreement.

### §L3 — NOT blind to a constant drift

Drift makes one sign likelier, and so removes changes:

| drift added to each return | median | mean |
|---|---|---|
| 0.000 | 9.0 | 9.3245 |
| 0.002 | 9.0 | 9.0223 |
| 0.010 | 6.0 | 5.2847 |
| 0.050 | 0.0 | 0.0000 |

### §L4 — blind to a time REVERSAL, which no other order change is

Reversing a window keeps every adjacency, so the count cannot move. Over 500
sampled windows of a walk a reversal left the count unchanged on **500 of
500** and a permutation on **70 of 500**. A consumer who expects a window
statistic to see direction is wrong about this one.

### §L5 — it is a STATE, not an event

Neighbouring windows share 19 of their 20 returns. Autocorrelation on the
walk: **0.9406** at lag 1, 0.6871 at lag 5, 0.3817 at lag 10, −0.1183 at lag
20 and 0.1842 at lag 40.

It is also coarse and heavily tied: 20 reachable values at `length` 20, of
which a 1,500-bar walk shows 13.

---

## §Z — cost

The module walks two `int64` prefix sums; the obvious alternative
materialises a `(rows, length)` window block. The two are the same column —
measured bit-equal on a 400,000-bar frame at both lengths — and what
separates them is memory:

| length | prefix-sum peak | windowed peak | same column |
|---|---|---|---|
| 20 | 29.7 MB | 139.2 MB | True |
| 250 | 29.7 MB | 1702.1 MB | True |

The prefix-sum peak does not grow with `length`; the block form's does,
linearly. ⚠ Peaks are a property of this run and are left out of §F2's
digest. TIME is deliberately not claimed.

---

## §W — the wiring

Five touch points, all asserted by
`tests/test_tf_zero_cross_20.py::test_the_five_wiring_touch_points`:

| # | file | what |
|---|---|---|
| 1 | `pandas_ta/statistics/tf_zero_cross_20.py` | the indicator |
| 2 | `pandas_ta/statistics/__init__.py` | package export |
| 3 | `pandas_ta/__init__.py` → `Category["statistics"]` | `df.ta.strategy()` |
| 4 | `pandas_ta/core.py` | `df.ta.tf_zero_cross_20()` |
| 5 | `tests/test_tf_zero_cross_20.py` | this suite |

Also updated: `README.md` (the statistics list and its count),
`docs/IndicatorDictionary.md` (regenerated), `docs/MLCompanionContract.md`
(the `SF` tally) and `tests/test_altport2_ports.py` (`CATEGORY_TOTAL`).

The dictionary shows the first paragraph after a docstring's title,
whitespace-squeezed and truncated at 150 characters
(`docs/gen_indicator_dictionary.py:290`, `desc(rec, limit=150)`), so the
overlap warning has to fit inside that. §W prints the paragraph and its
length: **146 characters**, four under the cut, so the warning reaches the
dictionary un-truncated.
`tests/test_tf_zero_cross_20.py::test_the_overlap_warning_survives_the_dictionary_cut`
applies the same squeeze-and-truncate — reading the limit out of
`gen_indicator_dictionary.py` rather than retyping it, so a narrower cut
fails the test instead of silently dropping the warning — and asserts
`LEAN_MOMERSION_20` survives it.
