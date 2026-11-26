# Same-day gap fill, signed — measured (`rd_gap_fill`)

Issue #174 (RD-GAP-FILL), from the 2026-10-25 ResearchIntel Reddit-KB scan, round 6
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
the screen prototype (`docs/issues/screen/ind_screen_r6.py`'s `rd_gap_fill`, which is
mathematically the same reading, confirmed by independent derivation below, but is not what
Gate A cites). This exact gap/fill definition is shared with the twin indicator
`rd_gap_fill_rate_60` (issue #165, already shipped, `pandas_ta/statistics/rd_gap_fill_rate_60.py`);
this port is the un-rolled, per-bar signed flag issue #174 asks for, not a 60-bar share.

**Status:** Gates A–F measured. Gate E SHIP (0.6597 vs `GAP_PCT`). Shipped.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/candles/rd_gap_fill.py` | candles | `RD_GAP_FILL_0.3` | `{-1.0, 0.0, 1.0}` or NaN |

Tests: `tests/test_rd_gap_fill.py` (20 tests). Numbers: `python docs/measure_rd_gap_fill.py`,
run from the repo root. Environment: Python 3.11.2, pandas 2.3.3, numpy 1.26.4.
Measured 2026-11-26.

## Decisions

1. **One parameter, `min_gap`, not a fixed threshold.** The poster's words give a gap
   definition, a fill definition and a 0.3% minimum; this port keeps the 0.3% as the
   `min_gap` default (the poster's own figure) rather than hard-coding it, matching the
   twin `rd_gap_fill_rate_60`'s own choice and the fork's convention for every other
   threshold-based indicator. There is no window parameter here — unlike the twin, this
   column is a per-bar flag, not a trailing share, so there is nothing to window.
2. **"Price returns to previous Close on the same day" is read as the same bar's
   high/low touching the prior close** — the only reading available to a module that
   receives one bar per trading day (no intraday series here, and none available in this
   worktree). An up-gap (`open` at least `min_gap` above the prior close) fills if that
   bar's `low` reaches back down to the prior close; a down-gap fills if that bar's `high`
   reaches back up to it. This matches the screen prototype's own reading exactly
   (`((g >= GAP) & (l <= pc)) - ((g <= -GAP) & (h >= pc))`), carried through unchanged and
   confirmed by an independent re-derivation from the issue's own restatement (not copied
   from the prototype's source) — see Gate A below.
3. **Signed, not two separate flags.** The issue's own candidate is "+1 gap up filled / -1
   gap down filled / 0" — a single signed column, not `RD_GAP_FILL_UP`/`RD_GAP_FILL_DOWN`.
   This matches the issue's explicit scale-free form and the twin `rd_horseshoe`'s own
   signed-flag convention for a bull/bear pair.
4. **The first bar's undefined gap is NaN, not 0.** Unlike the twin `rd_gap_fill_rate_60`
   (where a NaN `gap_pct` degrades a boolean sum to "no gap, contributes 0" inside a
   rolling window), this is a per-bar flag with nothing to roll: the output is explicitly
   masked to NaN wherever `prev_close` is NaN
   (`tests/test_rd_gap_fill.py::test_warmup_is_exactly_one_bar`), so the undefined first bar
   reads NaN, not a false "no gap" 0. Every *other* bar with a real `prev_close` but no gap
   (or a gap that fails the threshold) reads 0, verified separately
   (`test_no_gap_ever_reads_zero_not_nan`).
5. **Column name carries `min_gap`**, `RD_GAP_FILL_{min_gap*100:g}` — e.g. `RD_GAP_FILL_0.3`
   at the default, `RD_GAP_FILL_1` at `min_gap=0.01` — following the fork's convention of
   encoding every parameter that changes the output in the column name
   (`tests/test_rd_gap_fill.py::test_custom_min_gap_in_name`).

## Gate A — correctness

The issue's own formula (not the prototype — issue #174's explicit instruction), read
bar-by-bar in the module's docstring:

```
prev_close  = close[1]
gap_pct     = open / prev_close - 1
filled_up   = (gap_pct >=  min_gap) AND low  <= prev_close
filled_down = (gap_pct <= -min_gap) AND high >= prev_close
RD_GAP_FILL = +1 IF filled_up ELSE -1 IF filled_down ELSE 0
```

A 5-bar hand-derived fixture, every input bar and the expected output chosen on paper
before the module ran (`tests/test_rd_gap_fill.py::test_hand_derived_values`): bar0 has no
prior close (NaN by construction); bar1 opens 0.5% above a 100.0 prior close and its low
(99.8) reaches back to it — a filled up-gap, +1; bar2 opens 1.59% below a 100.6 prior close
but its high (100.5) does *not* reach back to it — an unfilled down-gap, 0; bar3 opens only
0.1% away from its prior close — below the 0.3% minimum, not a gap at all, 0; bar4 opens
1.30% below a 99.8 prior close and its high (99.9) does reach back to it — a filled
down-gap, -1. Measured (`python docs/measure_rd_gap_fill.py`): `[1.0, 0.0, 0.0, -1.0]` for
bars 1–4, bar 0 NaN — exactly as derived on paper.

A second fixture where every bar's `open` equals the prior `close` exactly (no gap ever)
reads 0.0 on every settled bar, never NaN beyond bar 0
(`test_no_gap_ever_reads_zero_not_nan`) — confirming the "no gap" and "gap but unfilled"
cases both collapse to 0, distinct only from the undefined first bar.

Two further checks close the gaps a review round flagged: the inclusive `|gap| >= min_gap`
boundary fires exactly at `gap_pct == min_gap`, proven with binary-exact values
(`min_gap=0.25`, `open/prev_close = 125.0/100.0 = 1.25`, so `gap_pct` lands on `min_gap`
bit-for-bit rather than merely near it — the issue's native 0.3% cannot be hit exactly in
binary floating point) (`test_gap_exactly_at_threshold_counts_as_a_gap`); and `min_gap`
actually gates the comparisons, not merely the column name — the same 0.5%-gap bar reads
+1 at the default `min_gap=0.003` and 0 at a stricter `min_gap=0.01`
(`test_min_gap_parameter_actually_changes_firing`).

## Gate B — causality

- **The real module never reads the future, swept, not spot-checked.** Two 1,600-bar
  synthetic frames (seeds 1 and 2) spliced at `J`: bars `< J` come only from seed 1 in both
  the base and the spliced frame, so if the module reads no later bar than `T` its output
  on `[0, J)` cannot move. Measured over **28 swept J values** (`J` = 100, 150, ..., 1450,
  `python docs/measure_rd_gap_fill.py`): **real module leaked at 0 of 28**.
- **The mutant (the final write `gap_fill.where(prev_close.notna())` with a `.shift(-1)`
  appended, reading one bar into the future) is live** (differs from the real module on the
  unperturbed frame) **and leaked at 9 of the same 28 swept J values.** A discrete
  {-1, 0, 1} flag is non-zero on only a minority of bars (an active gap-fill event: 648 of
  1,599 settled bars on the Gate C frame below), so most J land on a settled-zero stretch
  where a one-bar back-date has nothing to move — the same low-power pattern
  `rd_horseshoe`'s own test documents (caught at 24 of 293 there, a sparser ~8%-firing
  formation). `tests/test_rd_gap_fill.py::test_lookahead_mutant_is_caught` pins the measured
  structural bound ("caught at some J, not none") rather than the exact count, since the
  issue-solver's own CPU-variant rule forbids pinning an exact count that could move with
  the runner's dispatched float kernels.

## Gate C — reachability

Synthetic, from this session:

- **1,600-bar frame (seed 4):** 1,599 of 1,600 bars settle (1-bar warm-up); 648 of those
  are non-zero (318 up-fills, 330 down-fills) — both signs reachable, and the column is not
  constant.
- **10 independent 600-bar frames (seeds 100–109):** every frame settles on 599 of 600
  bars, with 215–272 non-zero bars per frame and both up- and down-fills present on every
  single seed (e.g. seed 103: 128 up / 99 down; seed 106: 135 up / 137 down) — reachability
  is not an artifact of one seed.
- `0 < fires < n`: 648 of 1,599 settled bars are non-zero on the 1,600-bar frame, strictly
  between 0 and the settled count, so a constant column cannot pass.
- **Real data:** Gate E run `is174-rd_gap_fill-8b5cdc38`: 398,760 non-NaN / 166,142
  non-zero of 398,849 pooled bars across 89 ALTPORT-1 frames, no `degenerate.csv` row.

## Gate D — scale-free

- **Power-of-two (x8, x64): bit-identical, 0 mismatches on 1,599 co-finite cells**
  (`tests/test_rd_gap_fill.py::test_power_of_two_scale_is_bit_identical`,
  `python docs/measure_rd_gap_fill.py`). `gap_pct` is a ratio and both fill checks compare
  like-for-like price terms, so an exact power-of-two rescale is an exponent shift on every
  operand — the correctly-rounded division and every comparison's truth value cannot move.
- **Non-power-of-two (x10, x3.7): measured 0 mismatches on 1,599 co-finite cells**, but this
  is reported as a measured tolerance bound, not a mathematical guarantee the way the
  power-of-two case is: each scaled operand carries its own last-bit rounding, so an
  isolated `gap_pct` within ~1e-15 relative of the 0.3% threshold could in principle flip
  sides. `tests/test_rd_gap_fill.py::test_other_scales_stay_within_a_tiny_tolerance` bounds
  this at 1% of valid bars rather than pinning exactly 0, since the CPU's dispatched float
  kernels, not this module's logic, decide the last bit (the issue-solver's own
  CPU-variant rule).
- `0 < fires < n`, not constant: 648 of 1,599 settled bars are non-zero on the 1,600-bar
  frame above, both +1 and -1 present (318 / 330).

## Gate E — attribution

Launcher's run (`is174-rd_gap_fill-8b5cdc38`, 89 ALTPORT-1 BIST frames, 398,849 bars,
687 comparators: 329 `compute_all` + 358 `ml_features` manifest; canary AKBNK.IS, BIENY.IS,
AGHOL.IS, SASA.IS bit-equal), recorded in `docs/gate_e_ledger.csv`:

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---|---|---|---|---|
| `RD_GAP_FILL_0.3` | 0.6597 | `GAP_PCT` (`compute_all`) | 398,760 | 0.6570 | **SHIP** |

0.6597 is under the 0.76 ship line (`r3-perframe-0.90` bands) both pooled and per-frame
(0.0% of frames at or above 0.90) — **SHIP**, column kept.

Module sha1 at this commit (LF-normalised, `python docs/measure_rd_gap_fill.py`):
`d7792481261756b4a1c2d8ca9d890b63b9b859a3`.

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole suite):

```
python -m pytest -q tests/test_rd_gap_fill.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

**1,614 passed, 7 skipped, 0 failed** — this receipt session, after recording the Gate E
ledger row above. `tests/test_rd_gap_fill.py` alone: 20 passed.

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in for a GitHub
runner without AVX-512 — the four features issue-solver's rules name, not this machine's
full dispatchable set, which also has `AVX512CD`/`AVX512_CLX`/`AVX512_CNL`/`AVX512_ICL`
enabled): `python docs/measure_rd_gap_fill_cpu.py` — **20 passed** (just
`tests/test_rd_gap_fill.py`; the ledger/readme/wiring modules above are not CPU-sensitive
and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 400 → 401 (`tests/test_altport2_ports.py`).
- README: 400 → 401 registered, 408 → 409 callable, candles (9) → (10).
- `docs/MLCompanionContract.md`: 745 → 746 tagged and 106 → 107 `BIN` (newest first in the
  chain). `RD_GAP_FILL_0.3` tags `BIN` because the output is a discrete {-1, 0, 1} flag, not
  a continuous magnitude — the dictionary generator's own probe frame confirms it
  (`docs/IndicatorDictionary.md`'s `rd_gap_fill` row), not merely asserted here.
- `docs/IndicatorDictionary.md`, regenerated with this environment's package. Its diff is
  the `rd_gap_fill` row (`RD_GAP_FILL_0.3` BIN, 1-bar warm-up), the three header counts, the
  candles section count, the no-transform-needed shortlist, and nothing else (checked:
  `git diff docs/IndicatorDictionary.md`).
- `Category`: `rd_gap_fill` is placed alphabetically between `ha` and `rd_horseshoe` in
  `candles`.
