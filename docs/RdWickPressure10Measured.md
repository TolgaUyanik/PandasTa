# Wick pressure: bear-candle lower wicks minus bull-candle upper wicks (10) — measured (`rd_wick_pressure_10`)

Issue #170 (RD-WICK-PRESSURE-10), from the 2026-10-25 ResearchIntel Reddit-KB scan, round 6
(`docs/issues/screen/candidates_r6.csv`). Crowd talk (Reddit, tier 4): the definition comes
from a post or comment, and nothing in this port tests what the poster says it does —
existence, not evidence.

**Source:** Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:pneq7k
(2021-09-13) https://www.reddit.com/r/algotrading/comments/pneq7k/ — the poster's words:
"sum the top wicks on bull candles on X candlestick M1 to measure 'bear defense power'".
Claimed use: wicks show who is stronger; the poster's own words say they found it mostly
useless — **not independently tested here either way.** A Reddit post is not a script, so
there is no source line number to cite; Gate A below reads the formula directly from the
issue's own restatement ("sum lower wick on bear candles - sum upper wick on bull
candles"), per its own instruction ("Gate A starts from the source formula, not the
prototype"), not from the screen prototype (`docs/issues/screen/ind_screen_r6.py`'s
`rd_wick_pressure_10`, which is mathematically the same reading but is not what Gate A
cites). The 10-bar window and the sum-of-ranges denominator are not in the poster's words
— the issue discloses both as the prototype's own choice ("scale-free form: over 10 bars,
divided by the sum of ranges"), kept here as the `length` default (not hard-coded) and the
normalisation that turns the column into a feature at all.

**Status:** shipped through Gates A–F plus wiring and tests. Gate E measured 2026-11-25:
SHIP.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/candles/rd_wick_pressure_10.py` | candles | `RD_WICK_PRESSURE_10` | bounded in `[-1, 1]` — each wick is bounded by its own bar's range, so neither leg of the numerator can exceed the denominator (see Decision 4); NaN if the window's range sum is 0 |

Tests: `tests/test_rd_wick_pressure_10.py` (19 tests). Numbers: `python
docs/measure_rd_wick_pressure_10.py`, run from the repo root. Environment: Python 3.11.2,
pandas 2.3.3, numpy 1.26.4. Measured 2026-11-25.

## Decisions

1. **Candle colour reads `close` vs `open`**, the standard reading this fork's other
   candle ports use (`rd_horseshoe`): `bear = close < open`, `bull = close > open`. A doji
   (`close == open`) is neither, so it contributes 0 to both legs — not a Gate A judgment
   call, the only reading available since the poster's words name "bear candle" / "bull
   candle" without defining them, and every other candle-colour port in this fork reads
   them the same way.
2. **The denominator is the prototype's disclosed choice, not the poster's.** The
   poster's own words give no normalisation at all — a raw sum of wick lengths is a
   price-level quantity, not an ML feature per this repo's contract (`CLAUDE.md`'s
   "Scale-free" rule). The issue's own prototype note ("scale-free form: over 10 bars,
   divided by the sum of ranges") is carried through unchanged: `SUM(high - low, length)`
   in the denominator.
3. **Window = 10 bars, fixed by the issue's own title** (`(10)`), not a Gate A judgment
   call. A `length` argument is still offered, as the fork's convention for a
   fixed-suffix port is a parameter with that default, not a hard constant
   (`osap_retskew_21`, `rd_gap_fill_rate_60`).
4. **A zero-range window reads NaN, not 0.** When every bar in the window is a doji with
   `high == low`, the denominator is 0 and `0 / 0` is already NaN in IEEE float; the
   explicit `.replace([inf, -inf], nan)` guards a case that cannot occur mathematically
   here (the numerator's magnitude can never exceed the denominator's, since each wick is
   bounded by its own bar's range) but is kept for the same defensive reason `sdiv` keeps
   it in the screen prototype.

## Gate A — correctness

The issue's own formula, read bar-by-bar:

```
bear       = close < open
bull       = close > open
lower_wick = (MIN(open, close) - low)  IF bear ELSE 0
upper_wick = (high - MAX(open, close)) IF bull ELSE 0
RD_WICK_PRESSURE_10 = (SUM(lower_wick, 10) - SUM(upper_wick, 10)) / SUM(high - low, 10)
```

A 4-bar hand-derived fixture, every input bar and the expected ratio chosen on paper
before the module ran (`tests/test_rd_wick_pressure_10.py::test_hand_derived_value`):
bar0 is bear (lower wick 1.0), bar1 bull (upper wick 1.0), bar2 bear (lower wick 1.0),
bar3 bull (upper wick 1.0). At `length=3`, window `[0,1,2]` reads `(2-1)/15 = 0.066667`
at bar2 (lower sum 2, upper sum 1, range sum 15) and window `[1,2,3]` reads
`(1-2)/16 = -0.0625` at bar3 (lower sum 1, upper sum 2, range sum 16); `python
docs/measure_rd_wick_pressure_10.py` reproduces both exactly.

Cross-checked against an independent per-bar Python loop built straight from the formula
above (not read from the module) on a 1,600-bar synthetic OHLC frame with explicit
bear/bull bodies and independently-drawn upper/lower wicks, `length=10`: **1,591 compared
bars, NaN masks identical, max|diff| = 0.000e+00** (`test_matches_an_independent_loop`,
`python docs/measure_rd_wick_pressure_10.py`).

## Gate B — causality

- **The real module never reads the future, swept, not spot-checked.** Two 1,600-bar
  synthetic frames (seeds 1 and 2) spliced at `J`: bars `< J` come only from seed 1 in both
  the base and the spliced frame, so if the module reads no later bar than `T` its output
  on `[0, J)` cannot move. Measured over **28 swept J values** (`J` = 100, 150, ..., 1450,
  `python docs/measure_rd_wick_pressure_10.py`): **real module leaked at 0 of 28**.
- **The mutant (the final ratio write with a `.shift(-1)` appended, reading one bar into
  the future) is live** (differs from the real module on the unperturbed frame) **and
  leaked at all 28 of the same 28 swept J values** — unlike a rare binary flag
  (`rd_horseshoe`'s mutant caught at only 24 of 293), this column is a continuous ratio
  built from rolling sums that moves on nearly every bar, so a one-bar back-date is caught
  everywhere it was swept (`tests/test_rd_wick_pressure_10.py::test_lookahead_mutant_is_caught`).

## Gate C — reachability

Synthetic, from this session (no real-data cache in this worktree):

- **1,600-bar frame (seed 4), default length 10:** 1,591 of 1,600 bars fire (9-bar
  warm-up); values range −0.2261 to 0.2139 across **1,591 distinct values** — not constant.
- **10 independent 600-bar frames (seeds 100–109):** every frame fires on 591 of 600 bars
  (fixed 9-bar warm-up), with the range spanning −0.2276 (seed 109) to 0.3013 (seed 106)
  across seeds — both signs reached on every seed tried, not just one.
- **Zero-range NaN** is reachable by construction
  (`test_zero_range_window_reads_nan`); not observed on the random synthetic frames above
  (independently-drawn, continuous-valued wicks essentially never all collapse to 0 in a
  10-bar window), which is expected, not a defect.
- **Real data** (Gate E run `is170-rd_wick_pressure_10-c96ae347`, 89 ALTPORT-1 frames,
  398,849 pooled bars): `RD_WICK_PRESSURE_10` is non-NaN on 398,043 of 398,849 pooled
  cells (801 of the 806 NaNs are the 89 frames' 9-bar warm-up) and non-zero on 337,496 of
  those; no `degenerate.csv` row for this column.

## Gate D — scale-free

- **Power-of-two (x8, x64): bit-identical, 0 mismatches on 1,591 co-finite cells**
  (`tests/test_rd_wick_pressure_10.py::test_power_of_two_scale_is_bit_identical`,
  `python docs/measure_rd_wick_pressure_10.py`). `lower_wick`, `upper_wick` and the range
  are each a difference of two like-for-like price terms on the same bar, so an exact
  power-of-two rescale is an exponent shift on every operand — both legs of the numerator
  and the denominator scale by the same `k`, leaving the ratio bit-identical.
- **Non-power-of-two (x10, x3.7): measured max|diff| 7.432e-15 / 5.600e-15 on 1,591
  co-finite cells** (1,582 / 1,587 of them differ at the last bit, all far under the
  test's 1e-9 tolerance) — reported as a measured tolerance bound, not a mathematical
  guarantee the way the power-of-two case is: each scaled operand carries its own
  last-bit rounding under a non-power-of-two factor.
- NaN masks match exactly at every factor. `0 < 1,591 fires < 1,600` bars, 1,591 distinct
  values (not a constant column) — the same frame as Gate C.

## Gate E — attribution

Run by issue-solver, `gate_e_overlap.py run --module pandas_ta.candles.rd_wick_pressure_10`,
89 ALTPORT-1 frames, 398,849 bars, canary bit-equal (AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS).
Output: `is170-rd_wick_pressure_10-c96ae347/overlap_max.csv`.

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---|---|---|---|---|
| `RD_WICK_PRESSURE_10` | 0.4599 | `qstick_pct` (manifest) | 398,043 | 0.4585 | SHIP |

0.4599 < 0.76 (SHIP band, `r3-perframe-0.90`): not a restatement of any shipped column.
Recorded in `docs/gate_e_ledger.csv` (measured 2026-11-25).

Quoted from the issue for context only (the prototype's own screen run, not this Gate E
run): same max |ρ| 0.4599 vs `qstick_pct`, next comparators `qstick_pct_Pctl` 0.4253,
`brar_AR_26` 0.4055. Fork overlap (stage 2, not Gate E, scale-free `Category` outputs at
defaults, 12 frames): max |ρ| 0.5029 vs `imi:IMI_14`, per-frame max median 0.4725 — not a
restatement at the 0.90 line. Pre-flight on 6 frames (`sanity_r6.csv`): prefix-causal,
unchanged under price ×8 and volume ×8.

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole suite):

```
python -m pytest -q tests/test_rd_wick_pressure_10.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

Re-measured after the ledger row was recorded (receipt session, 2026-11-25):
**1,589 passed, 7 skipped, 0 failed.** `tests/test_rd_wick_pressure_10.py` alone:
19 passed.

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in for a GitHub
runner without AVX-512 — the four features issue-solver's rules name, not this machine's
full dispatchable set, which also has `AVX512CD`/`AVX512_CLX`/`AVX512_CNL`/`AVX512_ICL`
enabled): `python docs/measure_rd_wick_pressure_10_cpu.py` — **19 passed** (just
`tests/test_rd_wick_pressure_10.py`; the ledger/readme/wiring modules above are not
CPU-sensitive and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 397 → 398 (`tests/test_altport2_ports.py`); candles bucket
  (not individually tracked in `CATEGORY_BUCKETS`) 7 → 8.
- README: 397 → 398 registered, 405 → 406 callable, candles (7) → (8).
- `docs/MLCompanionContract.md`: 742 → 743 tagged and 372 → 373 `SF` (newest first in the
  chain). `RD_WICK_PRESSURE_10` tags `SF` because both legs of the numerator and the
  denominator are sums of like-for-like price differences — the dictionary generator's
  own probe frame confirms it (`docs/IndicatorDictionary.md`'s `rd_wick_pressure_10` row),
  not merely asserted here.
- `docs/IndicatorDictionary.md`, regenerated with this environment's package. Its diff is
  the `rd_wick_pressure_10` row (`RD_WICK_PRESSURE_10` SF, 9-bar warm-up), the three
  header counts, the candles section count, the SF shortlist, and nothing else (checked:
  `git diff docs/IndicatorDictionary.md`).
- `Category`: `rd_wick_pressure_10` is placed alphabetically after `rd_outside_bar` in
  `candles`.

## Open

None. Gate E measured SHIP, ledger row recorded, #170 closes as a ship.
