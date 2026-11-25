# Outside bar: range engulfs the prior bar's range — measured (`rd_outside_bar`)

Issue #167 (RD-OUTSIDE-BAR), from the 2026-10-25 ResearchIntel Reddit-KB scan, round 6
(`docs/issues/screen/candidates_r6.csv`). Crowd talk (Reddit, tier 4): the definition
comes from a post or comment, and nothing in this port tests what the poster says it
does — existence, not evidence.

**Source:** Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:Trading:1og1s0z (2025-10-25)
https://www.reddit.com/r/Trading/comments/1og1s0z/; rd:Daytrading:1gxmcnv (2024-11-23)
https://www.reddit.com/r/Daytrading/comments/1gxmcnv/ — the poster's words: "Look at
where it sits relative to the prior candle." Claimed use: inside bar = compression,
outside bar = expansion; relative size shows volatility expanding/contracting — **not
independently tested here.** The issue itself gives the formula
(`high_t > high_{t-1} and low_t < low_{t-1}`), not a script, so there is no source line
number to cite; Gate A below reads the formula directly from the issue's own statement
(its own instruction: "Gate A starts from the source formula, not the prototype"), not
from the screen prototype (`docs/issues/screen/ind_screen_r6.py`'s `rd_outside_bar`,
which is mathematically the same reading but is not what Gate A cites).

**Status:** shipped through Gates A–F plus wiring and tests. Gate E measured
2026-11-25, run `is167-rd_outside_bar-3a7baac5`, SHIP.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/candles/rd_outside_bar.py` | candles | `RD_OUTSIDE_BAR` | `{0.0, 1.0}` or NaN |

Tests: `tests/test_rd_outside_bar.py` (20 tests). Numbers: `python docs/measure_rd_outside_bar.py`,
run from the repo root. Environment: Python 3.11.2, pandas 2.3.3, numpy 1.26.4. Measured
2026-11-25.

## Decisions

1. **The mirror of upstream `cdl_inside`.** `cdl_inside` fires on
   `high.diff() < 0 & low.diff() > 0` (current bar engulfed by the prior bar). Flipping
   both comparisons (`high.diff() > 0 & low.diff() < 0`, equivalently
   `high > high[1] and low < low[1]`) is exactly the issue's formula — read as a
   deliberate mirror of an existing indicator in this fork, not re-derived independently.
2. **Scale-free form is unsigned `{0, 1}`, not signed by candle colour.** The issue
   states this explicitly ("scale-free form: 1 / 0"), and the screen prototype's own
   reading (`((h > h.shift(1)) & (l < l.shift(1))).astype(float)`) carries no colour
   term either — unlike `rd_horseshoe`, open and close play no part in the formula and
   are not read by the module at all.
3. **Both sides of the engulf are required, not just one.** `high > high[1]` alone (the
   high side) or `low < low[1]` alone (the low side) must NOT fire — only the AND of
   both counts as "outside" (`tests/test_rd_outside_bar.py::test_high_side_only_does_not_fire`,
   `test_low_side_only_does_not_fire`).
4. **An exact tie on either side does not fire.** `high == high[1]` is not `high >
   high[1]`; the issue's strict inequalities are kept as given, so a bar whose high and
   low both exactly equal the prior bar's does not count as outside
   (`test_exact_tie_does_not_fire`).
5. **Only the first bar is warm-up NaN**, masked via `.where(prior_high.notna())` — a
   2-bar comparison needs exactly one prior bar, unlike `rd_horseshoe`'s 4-bar window.
6. **Column is `RD_OUTSIDE_BAR`, no parameters** — the comparison is fixed at a 2-bar
   window by the poster's own definition, so there is nothing to name a default against.

## Gate A — correctness

The issue's own formula (not the prototype — the issue's explicit instruction), read
bar-by-bar in the module's docstring:

```
RD_OUTSIDE_BAR = 1 IF high[T] > high[T-1] AND low[T] < low[T-1] ELSE 0
```

Four hand-derived fixtures (`python docs/measure_rd_outside_bar.py`,
`tests/test_rd_outside_bar.py`):

| fixture | bars (H/L) | result at bar 1 |
|---|---|---|
| fires | (101, 99) (102, 98) | `1.0` — high 102 > 101 AND low 98 < 99 |
| high_only | (101, 99) (102, 99.5) | `0.0` — high 102 > 101 but low 99.5 is NOT < 99 |
| low_only | (101, 99) (100.5, 98) | `0.0` — low 98 < 99 but high 100.5 is NOT > 101 |
| tie | (101, 99) (101, 99) | `0.0` — neither `>` nor `<` holds on an exact tie |

Confirmed by `python docs/measure_rd_outside_bar.py` (Gate A section): all four
fixtures reproduce the table above exactly.

## Gate B — causality

- **The real module never reads the future, swept, not spot-checked.** Two 600-bar
  synthetic frames (seeds 1 and 2) spliced at `J`: bars `< J` come only from seed 1 in
  both the base and the spliced frame, so if the module reads no later bar than `T` its
  output on `[0, J)` cannot move. Measured over **293 swept J values** (`J` = 10, 12, ...,
  594, `python docs/measure_rd_outside_bar.py`): **real module leaked at 0 of 293**.
- **A single fixed J is a weak catch here, like `smc_sweep` (`tests/test_altport2_ports.py`)
  and `rd_horseshoe`.** The pattern fires on a minority of bars (Gate C below), so a
  one-bar back-date only shows up when the bar adjacent to `J` happens to be an event.
  The mutant (the final write `outside.astype(float).where(prior_high.notna())` with a
  `.shift(-1)` appended, reading one bar into the future) is live (differs from the real
  module on the unperturbed frame) and **leaked at 35 of the same 293 swept J values** —
  enough to prove it is caught, not enough to expect it at every J
  (`tests/test_rd_outside_bar.py::test_mutant_is_caught_across_a_sweep_of_perturbation_points`).

## Gate C — reachability

Synthetic, from this session (no real-data cache in this worktree; the receipt session
adds the Gate E run's real-data reachability count):

- **2,000-bar frame (seed 4):** 1,999 of 2,000 bars fire-eligible (1-bar warm-up);
  **242 outside bars, 1,757 at zero** — not constant
  (`tests/test_rd_outside_bar.py::test_fires_and_is_not_constant`).
- **10 independent 600-bar frames (seeds 100–109):** fire counts 55–78 of 599 settled
  bars per frame — the pattern fires on every one of the 10 frames, not just the frame
  the reachability test happens to use.
- What blanks a bar: the 1-bar warm-up (no prior bar); nothing else, since every input
  bar after that is a valid high/low pair by construction.

## Gate D — scale-free

- x8, x64 (power-of-two), and x10, x3.7 (not powers of two): **bit-identical, 0
  mismatches on 599 co-finite cells** at every one of the four factors
  (`tests/test_rd_outside_bar.py::test_price_scale_is_bit_identical`,
  `python docs/measure_rd_outside_bar.py`). Unlike a continuous-magnitude column, there
  is no tolerance band to report separately for the non-power-of-two factors: both terms
  in the chain are comparisons (`>`, `<`) between like-for-like price terms (a high
  against a prior high, a low against a prior low), so a positive rescale preserves
  every comparison's truth value exactly, not merely approximately.
- `0 < fires < n`, and the column is not constant: 242 of 1,999 settled bars fire on the
  2,000-bar frame above.

## Gate E — attribution

Measured by the launcher 2026-11-25, run `is167-rd_outside_bar-3a7baac5`
(`gate_e_overlap.py run --module pandas_ta.candles.rd_outside_bar`), 89 ALTPORT-1 BIST
frames, 398,849 pooled bars, 329 + 358 = 687 comparators, canary bit-equal on AKBNK.IS,
BIENY.IS, AGHOL.IS, SASA.IS.

| column | max \|ρ\| | against | n | per-frame max median | verdict |
|---|---|---|---|---|---|
| `RD_OUTSIDE_BAR` | 0.3389 | `LOWER_LOW` | 398,760 | 0.3384 | **SHIP** |

0.3389 is well under the DISCLOSE line (0.76), so `RD_OUTSIDE_BAR` ships as-is — no
column removed.

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole suite):

```
python -m pytest -q tests/test_rd_outside_bar.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

**1,566 passed, 7 skipped, 1 failed** (`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
— expected per the issue-solver rules: this port has no ledger row until the launcher's
Gate E run and the receipt session record it). `tests/test_rd_outside_bar.py` alone:
20 passed.

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in for a GitHub
runner without AVX-512 — the four features issue-solver's rules name, not this machine's
full dispatchable set, which also has `AVX512CD`/`AVX512_CLX`/`AVX512_CNL`/`AVX512_ICL`
enabled): `python docs/measure_rd_outside_bar_cpu.py` — **20 passed** (just
`tests/test_rd_outside_bar.py`; the ledger/readme/wiring modules above are not
CPU-sensitive and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 395 → 396 (`tests/test_altport2_ports.py`).
- README: 395 → 396 registered, 403 → 404 callable, candles (6) → (7).
- `docs/MLCompanionContract.md`: 740 → 741 tagged and 105 → 106 `BIN` (newest first in
  the chain). `RD_OUTSIDE_BAR` tags `BIN` because the output is a discrete `{0, 1}` flag,
  not a continuous magnitude — the dictionary generator's own probe frame confirms it
  (`docs/IndicatorDictionary.md`'s `rd_outside_bar` row), not merely asserted here.
- `docs/IndicatorDictionary.md`, regenerated with this environment's package. Its diff is
  the `rd_outside_bar` row (`RD_OUTSIDE_BAR` BIN, 1-bar warm-up), the three header counts,
  the candles section count, the BIN/ORD shortlist, and nothing else (checked:
  `git diff docs/IndicatorDictionary.md`).
- `Category`: `rd_outside_bar` is placed alphabetically last in `candles`, after
  `rd_horseshoe`.
