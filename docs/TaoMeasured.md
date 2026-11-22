# TAO-10-5 — `tao` measured (PandasTa issue #266)

The trend-adjusted stochastic oscillator, `(10, 5, 50)`. Module
`pandas_ta/momentum/tao.py`, tests `tests/test_tao.py`.

    O[T]     = 100 * (close[T] - LL10[T]) / (HH10[T] - LL10[T])   (NaN if HH == LL)
    MAO[T]   = mean(O[T - 4 .. T])
    TAO_10_5 = O[T] - (MAO[T] - 50)

Source: Perry J. Kaufman, *Trading Systems and Methods*, 5th ed. (Wiley, 2013),
ch. 17, crediting E. Marshall Wall, "Rolling with the Punches", *Futures* (July
1996). The book applies it to "stochastics or other oscillators" with a 10-day
oscillator and a 5-day average; its formula for the oscillator is garbled in the
text available, so the raw stochastic %K(10) is the owner's choice of
2026-11-08 (issue #266). Gate A starts from the issue's formula, not from a
prototype and not from a reading of the book. Existence, not evidence: nothing
here tests predictive value.

**Every number below is printed by `python docs/measure_tao.py`** (one section
per gate limb; `python docs/measure_tao.py A1 D` for named sections). The same
figures appear in the module docstring and in `tests/test_tao.py`, and this file
is the only place they may come from.

Measured 2026-11-18 on this machine: pandas 2.3.3, numpy 1.26.4, Python 3.11.

⚠ **Every count here is SYNTHETIC except Gate E**, measured 2026-11-22 by the
owner on BIST (DISCLOSE, see Gate E below; that run is also Gate C's real-data limb).

## The frames

Eight OHLC frames of 1,500 bars, built from a close path, an open one bar behind
it, and a high / low outside both by a random non-negative spread that is zero on
~20% of bars, so the close is often exactly the bar's extreme: `walk`, `trend`,
`range-bound` (AR(1) in log price), `grid` (0.01 tick), `heavy-tailed` (t, 2 dof),
`jump` (×1.5 at bar 750), `flat` (every price 100.0), `coarse` (σ 0.002 rounded
to a 0.5 tick, so a close sits on the window's extreme by rounding).
`tests/test_tao.py` uses the same builders and seeds at 400 bars.

## Gate A — correctness

### §A1 the issue's formula by explicit scalar loops

A fresh 10-bar min / max and a fresh five-term mean per bar, no pandas operation.

| frame | fired | bit-equal | masks equal | bars differ | max abs (points) | Spearman |
|---|---|---|---|---|---|---|
| walk | 1487 | False | True | 660 | 2.842e-14 | 1.0000 |
| trend | 1487 | False | True | 520 | 2.842e-14 | 1.0000 |
| range-bound | 1487 | False | True | 951 | 2.842e-14 | 1.0000 |
| grid | 1487 | False | True | 509 | 2.842e-14 | 1.0000 |
| heavy-tailed | 1487 | False | True | 565 | 2.842e-14 | 1.0000 |
| jump | 1487 | False | True | 814 | 4.263e-14 | 1.0000 |
| flat | 0 | True | True | 0 | — | — |
| coarse | 1487 | False | True | 156 | 1.421e-14 | 0.9999 |

The NaN masks match on every frame. Values are not bit-equal, because pandas'
rolling mean is an online add/remove accumulator and a fresh five-term sum is
not. The test asserts 1e-10 points.

### §A2 `TAO = 50 + (O - MAO)`

The issue's form and the deviation form differ by at most 1.421e-14 points on the
seven firing frames (7.105e-15 on `trend`).

### §A3 the reading NOT taken: the shipped `stoch`'s raw %K

`stoch(k=10, d=1, smooth_k=1)` divides by `non_zero_range`, which adds an epsilon
on a zero range. On the seven moving frames the column built on it is
**bit-identical** to this module (0 bars differ). On `flat` it differs on all
1,487 bars: it reads a number where the issue's definition reads NaN. The module
retypes the two lines instead of importing `stoch` for that reason. It also uses
`rolling(...).mean()` rather than `sma`, because `sma` dispatches to TA-Lib when
TA-Lib is importable.

## Gate B — causality

### §B the blind sweep

For each boundary j, two frames agree bit for bit on bars < j and differ wholly
on bars >= j: each later bar's four prices are scaled by one per-bar factor in
[1, 4], up in one future and down in the other, so it stays a valid OHLC bar.
**0 of 1,499 offsets caught on each of the eight frames.**

### §B1 five look-ahead mutants, read off the shipped source

Each is an edit to the shipped file, `exec`'d in memory. Live = the mutant's
output differs from the module's on that many of the eight frames. Caught counts
are over the 36 tail offsets 1464 .. 1499.

| mutant | live | walk | trend | range-bound | grid | heavy-tailed | jump | flat | coarse |
|---|---|---|---|---|---|---|---|---|---|
| ll-centred | 7 | 36 | 36 | 36 | 36 | 36 | 36 | 0 | 36 |
| hh-lead | 7 | 35 | 36 | 36 | 33 | 36 | 35 | 0 | 36 |
| close-lead | 7 | 36 | 36 | 36 | 36 | 36 | 36 | 0 | 36 |
| mao-centred | 7 | 36 | 36 | 36 | 36 | 36 | 36 | 0 | 36 |
| output-early | 7 | 36 | 36 | 36 | 36 | 36 | 36 | 0 | 36 |

⚠ `hh-lead` misses up to 3 of the 36 offsets on some frames. The likely
mechanism (not separately measured) is that when the future bar's high stays
under the window's maximum in both futures, HH comes out the same and the
prefix is bit-equal. The test asserts it caught on at least half the offsets of
every firing frame, not on all. Every mutant is invisible on `flat`, where both
outputs are all-NaN.

## Gate C — reachability

| frame | bars | fired | first | distinct | min | max | < 0 | > 100 | flat 10-bar windows |
|---|---|---|---|---|---|---|---|---|---|
| walk | 1500 | 1487 | 13 | 1487 | -12.8204 | 119.9993 | 4 | 10 | 0 |
| trend | 1500 | 1487 | 13 | 1487 | -8.2279 | 107.0204 | 3 | 1 | 0 |
| range-bound | 1500 | 1487 | 13 | 1486 | -11.1808 | 116.9872 | 17 | 21 | 0 |
| grid | 1500 | 1487 | 13 | 1487 | -2.8230 | 112.6194 | 3 | 6 | 0 |
| heavy-tailed | 1500 | 1487 | 13 | 1487 | -17.4332 | 118.0762 | 18 | 14 | 0 |
| jump | 1500 | 1487 | 13 | 1487 | -13.7893 | 110.6496 | 9 | 7 | 0 |
| flat | 1500 | 0 | — | 0 | — | — | 0 | 0 | 1491 |
| coarse | 1500 | 1487 | 13 | 312 | 1.3333 | 86.6667 | 0 | 0 | 0 |

The warm-up is a constant 13 bars (`length + ma_length - 2`), and every bar after
it fires on the seven moving frames. `flat` fires 0. The column overshoots
[0, 100] on six of the seven moving frames, as the issue says it can.

**The bound is [-30, 130]**, because `O` is one of the five terms of its own mean,
so `O - MAO = 0.8 O - (other four) / 5` lies in [-80, 80]. It is attained exactly
on a hand frame (a 0 .. 100 range, four closes at the low, then one at the high):
`130.0`, and `-30.0` for the mirror.

### §C2 flat windows: what empties the column

A run of L identical bars (high == low == close) planted in `walk`, ending at
bar 800:

| L | NaN `O` bars | TAO bars emptied |
|---|---|---|
| 5 | 0 | 0 |
| 9 | 0 | 0 |
| 10 | 1 | 5 |
| 11 | 2 | 6 |
| 15 | 6 | 10 |

Each NaN `O` empties the five means whose window contains it. `coarse` has 0 flat
10-bar windows, so a synthetic tick frame does not stand in for real-data
flatness. The real count is part of the owed Gate C limb.

## Gate D — scale-free

The price enters only as `(close - LL) / (HH - LL)`. On all seven firing
frames, ×8, ×64, ×2^-20 and ×2^300 are **bit-identical**. ×10, ×3.7 and ×0.1
keep the NaN masks identical, and the values move by at most 8.242e-13 points
(on `coarse`, where ×10 is also bit-identical). Spearman is 1.0000, except
0.9996 on `coarse` at ×3.7 and ×0.1. `flat` is bit-identical under the exact
factors too, as all-NaN. A level shift cancels in exact arithmetic but not bit
for bit. On `walk`, adding 1 / 50 / 1e6 keeps the masks identical and moves the
values by 3.837e-13 / 1.307e-12 / 6.354e-09 points.
`0 < fires < n` holds on the seven firing frames (1,487 of 1,500).

## Gate E — attribution: DISCLOSE (ships disclosed)

Measured 2026-11-22 by the owner on this module, after the branch was merged
with `dev`; row `pr350-tao` in `docs/gate_e_ledger.csv`. `gate_e_overlap.py run
--module pandas_ta.momentum.tao` over the 89 BIST frames, 687 comparators,
canary bit-equal:

| column | max \|ρ\| | against | set | n | per-frame max median | verdict |
|---|---|---|---|---|---|---|
| `TAO_10_5` | 0.7879 | `cfo` | compute_all | 397,675 | 0.7894 | DISCLOSE |

Next comparators: `cfo_ta_Pctl` 0.7682 and `cfo_ta` 0.7653 (manifest),
`Dist_to_hma_pct_Pctl` 0.7393. The band is DISCLOSE (0.76 ≤ ρ < 0.80,
`CLAUDE.md` Gate E row): the column ships, with this overlap disclosed. The top
comparator is the engine's Chande Forecast Oscillator. That fits the synthetic
§F reading below, where `CFO_9` already reached 0.84 on `range-bound`.

### §F non-redundancy against the fork's own columns, synthetic

⚠ A disclosure, not a gate. Spearman of `TAO_10_5` against:

| frame | WILLR_10 | STOCHk_10_3_3 | STOCHk_14_3_3 | CFO_9 | RANK_5 |
|---|---|---|---|---|---|
| walk | 0.5135 | 0.1514 | 0.0333 | 0.8115 | 0.7709 |
| trend | 0.5721 | 0.1516 | 0.0788 | 0.7830 | 0.7331 |
| range-bound | 0.6200 | 0.1874 | 0.0516 | 0.8355 | 0.8464 |
| grid | 0.5043 | 0.1430 | 0.0473 | 0.8287 | 0.7671 |
| heavy-tailed | 0.5139 | 0.1620 | 0.0404 | 0.7423 | 0.7542 |
| jump | 0.5287 | 0.1621 | 0.0336 | 0.8315 | 0.7932 |
| coarse | 0.5481 | 0.1506 | 0.0368 | 0.7395 | 0.6585 |

Subtracting the 5-bar mean turns a range position into short-horizon momentum.
The raw %K it is built on (`WILLR_10`, i.e. %K - 100) is only 0.50 .. 0.62, while
`CFO_9` reaches 0.84 and `RANK_5` 0.85 on `range-bound`. **The real Gate E run
may land in DISCLOSE or DISCLOSE_GAP against one of these**, and this table is
the reason to look there first.

## §W Wiring — the five touch points

1 module `pandas_ta/momentum/tao.py` · 2 `ta.momentum.tao` True · 3
`Category["momentum"]` True (momentum has 88, `Category` total 358) · 4
`df.ta.tao` True, bit-equal to the function · 5 `tests/test_tao.py`. Column
`TAO_10_5`. A non-default midpoint is appended (`TAO_14_3_40`), because the
issue's name has no slot for it. The docstring's first paragraph is 135
characters and survives the dictionary's 150-character cut whole.
`docs/IndicatorDictionary.md` tags `TAO_10_5` `SF`. The census moves 702 → 703
tagged columns and 340 → 341 `SF`.

## §Z Cost

Vectorised throughout, no Python loop: one rolling min, one rolling max, one
rolling mean, and arithmetic.

| bars | traced peak MB | ms | ms (2nd) |
|---|---|---|---|
| 100,000 | 5.6 | 7.9 | 7.6 |
| 400,000 | 22.4 | 32.6 | 32.1 |

The wall clock is this machine's and this run's.

## Gate F — suites

The targeted run named in the session brief: `tests/test_tao.py` (142 passed), together with
`test_altport2_ports.py`, `test_gate_e_ledger.py`, `test_indicator_list_tables.py`,
`test_readme_counts.py` and `test_wiring_accessors.py`: 1,333 passed, 8 skipped. The full suite
and the Backtesting suite are run by the orchestrator.

## Decision

Ship through Gates A–E. Gate E is DISCLOSE (0.7879 vs `cfo`), so the column
ships with that overlap disclosed.
