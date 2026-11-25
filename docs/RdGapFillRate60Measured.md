# Share of 0.3%+ gaps filled the same day, trailing 60 bars — measured (`rd_gap_fill_rate_60`)

Issue #165 (RD-GAP-FILL-RATE-60), from the 2026-10-25 ResearchIntel Reddit-KB scan, round 6
(`docs/issues/screen/candidates_r6.csv`). Crowd talk (Reddit, tier 4): the definition comes
from a post or comment, and nothing in this port tests what the poster says it does —
existence, not evidence.

**Source:** Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:Daytrading:1r3r2qn (2026-02-13)
https://www.reddit.com/r/Daytrading/comments/1r3r2qn/; rd:swingtrading:1r3w6ms (2026-02-13)
https://www.reddit.com/r/swingtrading/comments/1r3w6ms/; rd:algotrading:1mulzoh (2025-08-19)
https://www.reddit.com/r/algotrading/comments/1mulzoh/ — the poster's words: "Gap
definition: Open vs previous Close. Minimum gap: 0.3% (filters out noise). Fill
definition: Price returns to previous Close on the same day." Claimed use: small gaps on
low volume fill often, large gaps less so, used as a fade/follow filter — **not
independently tested here.** A Reddit post is not a script, so there is no source line
number to cite; Gate A below reads the formula directly from the issue's own restatement
(its own instruction: "Gate A starts from the source formula, not the prototype"), not from
the screen prototype (`docs/issues/screen/ind_screen_r6.py`'s `rd_gap_fill_rate_60`, which
is mathematically the same reading but is not what Gate A cites). The 60-bar window is not
in the poster's words — the issue discloses it as the prototype's own choice, kept here as
the `length` default, not hard-coded.

**Status:** Gates A–E measured, **SHIP**. Port wired, ledger row recorded.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/statistics/rd_gap_fill_rate_60.py` | statistics | `RD_GAP_FILL_RATE_60_0.3` | `[0.0, 1.0]` or NaN |

Tests: `tests/test_rd_gap_fill_rate_60.py` (19 tests). Numbers: `python
docs/measure_rd_gap_fill_rate_60.py`, run from the repo root. Environment: Python 3.11.2,
pandas 2.3.3, numpy 1.26.4. Measured 2026-11-25.

## Decisions

1. **Two parameters, not a fixed window.** The poster's words give a gap definition, a
   0.3% minimum, and a fill definition, but no window length; the issue's own text
   discloses "60-bar window is this prototype's choice" for the screen candidate. This port
   keeps both as parameters — `length` (default 60) and `min_gap` (default 0.003, the
   poster's own 0.3%) — rather than hard-coding either, matching the fork's convention for
   every other rolling-share indicator (`lot_zeroret_60`, `ttr_snr_20`).
2. **"Price returns to previous Close on the same day" is read as the same bar's
   high/low touching the prior close** — the only reading available to a module that
   receives one bar per trading day (no intraday series here, and none available in this
   worktree). An up-gap (`open` at least `min_gap` above the prior close) fills if that
   bar's `low` reaches back down to the prior close; a down-gap fills if that bar's `high`
   reaches back up to it. This matches the screen prototype's own reading exactly
   (`((g >= GAP) & (l <= pc)) | ((g <= -GAP) & (h >= pc))`), carried through unchanged.
3. **The denominator is gaps, not all bars** — `SUM(filled, length) / SUM(is_gap,
   length)`, so the column answers "of the gaps that happened, what share filled", not
   "what share of all bars had a filled gap". A window with zero gaps reads NaN (0/0 in
   IEEE float), not 0, per the issue's own disclosure ("NaN with no gap") —
   `tests/test_rd_gap_fill_rate_60.py::test_no_gap_in_window_reads_nan`.
4. **The first bar's undefined gap is read as "not a gap"** (comparison against a NaN
   `gap_pct` is `False`, not `NaN`, in pandas/numpy), so it contributes 0 to both the
   numerator and the denominator rather than being excluded from the window. This matches
   the screen prototype's own math bar-for-bar (it applies the identical `rolling(60).sum()`
   over the same boolean construction, with no masking of the first bar either) — the port
   is not introducing a new warm-up assumption, only citing the poster's words for the
   gap/fill *definitions* while keeping the prototype's own warm-up arithmetic. The same
   mechanism applies to any mid-series NaN in `open`/`high`/`low`/`close` on a gappy real
   frame, not only the first bar: a NaN anywhere in those four inputs makes both `is_gap`
   and `filled` `False`, so the bar reads "no gap" rather than NaN — this would understate
   NaN on a gappy frame with real-world missing data.
5. **Column name carries both parameters**, `RD_GAP_FILL_RATE_{length}_{min_gap*100:g}` —
   e.g. `RD_GAP_FILL_RATE_60_0.3` at defaults, `RD_GAP_FILL_RATE_20_1` at `length=20,
   min_gap=0.01` — following the fork's convention of encoding every parameter that
   changes the output in the column name (`tests/test_rd_gap_fill_rate_60.py::test_custom_length_and_min_gap_in_name`).

## Gate A — correctness

The issue's own formula (not the prototype — issue #165's explicit instruction), read
bar-by-bar in the module's docstring:

```
prev_close = close[1]
gap_pct    = open / prev_close - 1
is_gap     = ABS(gap_pct) >= min_gap
filled     = (gap_pct >=  min_gap AND low  <= prev_close)
          OR (gap_pct <= -min_gap AND high >= prev_close)
RD_GAP_FILL_RATE = SUM(filled, length) / SUM(is_gap, length)   (NaN with no gap)
```

A 4-bar hand-derived fixture, every input bar and the expected output chosen on paper
before the module ran (`tests/test_rd_gap_fill_rate_60.py::test_hand_derived_value`):
bar0 has no prior close (not a gap by construction); bar1 opens 0.5% above a 100.0 prior
close and its low (99.8) reaches back to it — a filled up-gap; bar2 opens 1.59% below a
100.6 prior close but its high (100.5) does *not* reach back to it — an unfilled down-gap;
bar3 opens only 0.1% away from its prior close — below the 0.3% minimum, not a gap at all.
At `length=3`, both windows that include bars 1 and 2 (indices 2 and 3) read `1/2 = 0.5`
(one filled gap of two). A fifth fixture, every bar's open exactly equal to the prior
close, has zero gaps in every window and reads NaN, not 0
(`test_no_gap_in_window_reads_nan`).

Cross-checked against an independent per-bar Python loop built straight from the formula
above (not read from the module) on a 1,600-bar synthetic OHLC frame with explicit
overnight gaps (std ≈ 0.6%, so many cross and many miss the 0.3% threshold) and an
intraday range wide enough that some gaps fill and some do not: NaN masks identical, values
within `rtol=1e-12` (`test_matches_an_independent_loop`,
`python docs/measure_rd_gap_fill_rate_60.py`).

## Gate B — causality

- **The real module never reads the future, swept, not spot-checked.** Two 1,600-bar
  synthetic frames (seeds 1 and 2) spliced at `J`: bars `< J` come only from seed 1 in both
  the base and the spliced frame, so if the module reads no later bar than `T` its output
  on `[0, J)` cannot move. Measured over **28 swept J values** (`J` = 100, 150, ..., 1450,
  `python docs/measure_rd_gap_fill_rate_60.py`): **real module leaked at 0 of 28**.
- **The mutant (the final write `rate.where(gap_count > 0)` with a `.shift(-1)` appended,
  reading one bar into the future) is live** (differs from the real module on the
  unperturbed frame) **and leaked at 18 of the same 28 swept J values.** Unlike a rare
  binary flag (`rd_horseshoe`'s ~8%-firing pattern caught its mutant at only 24 of 293), this
  column is a continuous ratio that moves on almost every bar, so the mutant is caught at a
  majority of J, not merely "some" (`tests/test_rd_gap_fill_rate_60.py::test_lookahead_mutant_is_caught`,
  which pins `>= 14 of 28` as the structural bound rather than the exact bit-level count, since
  the issue-solver's own CPU-variant rule forbids pinning an exact count that could move with
  the runner's dispatched float kernels).

## Gate C — reachability

**Real data** (run `is165-rd_gap_fill_rate_60-0bbf164d`, 89 ALTPORT-1 BIST frames, 398,849
pooled bars): `RD_GAP_FILL_RATE_60_0.3` is non-NaN on 393,598 of the 398,849 pooled cells, and
every one of those 393,598 is non-zero — bounded away from both 0 and `n` on real prices. The
single `degenerate.csv` row in that run is comparator-side (`squeeze_SQZ_NO`, constant), not
this column.

Synthetic, from this session:

- **1,600-bar frame (seed 4):** 1,541 of 1,600 bars fire (59-bar warm-up); values range
  0.4706–0.8649 across 181 distinct values — not constant, and never exactly 0 or 1 on this
  seed (expected: a 60-bar window with std ≈ 0.6% gaps and threshold 0.3% almost always
  holds several gaps, some filled and some not).
- **10 independent 600-bar frames (seeds 100–109):** every frame fires on 541 of 600 bars
  (the fixed 59-bar warm-up), with the share ranging roughly 0.36–0.84 across seeds — both
  low and high shares reachable, not just one narrow band.
- **Zero-gap NaN** is reachable by construction (`test_no_gap_in_window_reads_nan`); not
  observed on the random synthetic frames above (a 60-bar window with these gap statistics
  essentially always holds at least one gap), which is expected, not a defect.

## Gate D — scale-free

- **Power-of-two (x8, x64): bit-identical, 0 mismatches on 1,541 co-finite cells**
  (`tests/test_rd_gap_fill_rate_60.py::test_power_of_two_scale_is_bit_identical`,
  `python docs/measure_rd_gap_fill_rate_60.py`). `gap_pct` is a ratio and both fill checks
  compare like-for-like price terms, so an exact power-of-two rescale is an exponent shift
  on every operand — the correctly-rounded division and every comparison's truth value
  cannot move.
- **Non-power-of-two (x10, x3.7): measured 0 mismatches on 1,541 co-finite cells**, but this
  is reported as a measured tolerance bound, not a mathematical guarantee the way the
  power-of-two case is: each scaled operand carries its own last-bit rounding, so an
  isolated `gap_pct` within ~1e-15 relative of the 0.3% threshold could in principle flip
  sides. `tests/test_rd_gap_fill_rate_60.py::test_other_scales_stay_within_a_tiny_tolerance`
  bounds this at 1% of valid bars rather than pinning exactly 0, since the CPU's dispatched
  float kernels, not this module's logic, decide the last bit (the issue-solver's own
  CPU-variant rule).
- `0 < fires < n`, not constant: 1,541 of 1,600 bars fire on the 1,600-bar frame above,
  181 distinct values, min 0.4706 and max 0.8649 both strictly inside `[0, 1]`.

## Gate E — attribution

Run `is165-rd_gap_fill_rate_60-0bbf164d` by issue-solver (launcher), `screen_r6`-style
harness, 89 ALTPORT-1 BIST frames, 398,849 pooled bars, 687 comparators (329 `compute_all` +
358 `ml_features` manifest), canary bit-equal on AKBNK.IS/BIENY.IS/AGHOL.IS/SASA.IS. Recorded in
`docs/gate_e_ledger.csv` (`python docs/gate_e_ledger.py record ... --measured 2026-11-25`).

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | per-frame max median against | verdict |
|---|---|---|---|---|---|---|
| `RD_GAP_FILL_RATE_60_0.3` | 0.2644 | `ZIGZAG` | 33,262 | 0.3471 | `CHANNEL_WIDTH` | **SHIP** |

Below both bands (`r3-perframe-0.90`): pooled 0.2644 and per-frame max median 0.3471 are far
under the 0.76 ship line, let alone the 0.90 struck line. Nothing struck; the column ships
as-is.

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole suite):

```
python -m pytest -q tests/test_rd_gap_fill_rate_60.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

**1,549 passed, 7 skipped, 1 failed** — the one failure was
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, expected before the
ledger row existed and resolved by the row recorded above (see Gate E above).
`tests/test_rd_gap_fill_rate_60.py` alone: 19 passed.

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in for a GitHub
runner without AVX-512 — the four features issue-solver's rules name, not this machine's
full dispatchable set, which also has `AVX512CD`/`AVX512_CLX`/`AVX512_CNL`/`AVX512_ICL`
enabled): `python docs/measure_rd_gap_fill_rate_60_cpu.py` — **19 passed** (just
`tests/test_rd_gap_fill_rate_60.py`; the ledger/readme/wiring modules above are not
CPU-sensitive and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 393 → 394 (`tests/test_altport2_ports.py`).
- README: 393 → 394 registered, 401 → 402 callable, statistics (80) → (81).
- `docs/MLCompanionContract.md`: 738 → 739 tagged and 369 → 370 `SF` (newest first in
  the chain). `RD_GAP_FILL_RATE_60_0.3` tags `SF` because the output is already a
  dimensionless ratio of two rolling counts, bounded in `[0, 1]` — the dictionary
  generator's own probe frame confirms it (`docs/IndicatorDictionary.md`'s
  `rd_gap_fill_rate_60` row), not merely asserted here.
- `docs/IndicatorDictionary.md`, regenerated with this environment's package. Its diff is
  the `rd_gap_fill_rate_60` row (`RD_GAP_FILL_RATE_60_0.3` SF, 59-bar warm-up), the three
  header counts, the statistics section count, the no-transform-needed shortlist, and
  nothing else (checked: `git diff docs/IndicatorDictionary.md`).
- `Category`: `rd_gap_fill_rate_60` is placed alphabetically between `rank` and `skew` in
  `statistics`.
