# Horseshoe 4-bar formation, signed — measured (`rd_horseshoe`)

Issue #164 (RD-HORSESHOE), from the 2026-10-25 ResearchIntel Reddit-KB scan, round 6
(`docs/issues/screen/candidates_r6.csv`). Crowd talk (Reddit, tier 4): the definition
comes from a post or comment, and nothing in this port tests what the poster says it
does — existence, not evidence.

**Source:** Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:Daytrading:1rwgrts
(2026-03-17) https://www.reddit.com/r/Daytrading/comments/1rwgrts/ — the poster's words:
"Bullish Horseshoe: Composed of Red-Green-Red-Green candles in order." Claimed use:
candlestick confirmation of reversal zones at range deviations — **not independently
tested here.** A Reddit post is not a script, so there is no source line number to cite;
Gate A below reads the formula directly from the issue's own restatement (its own
instruction: "Gate A starts from the source formula, not the prototype"), not from the
screen prototype (`docs/issues/screen/ind_screen_r6.py`'s `rd_horseshoe`, which is
mathematically the same reading but is not what Gate A cites).

**Status:** shipped through Gates A–F. Gate E measured 2026-11-25, max |ρ| 0.2168 <
0.76, SHIP.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/candles/rd_horseshoe.py` | candles | `RD_HORSESHOE` | `{-1.0, 0.0, 1.0}` or NaN |

Tests: `tests/test_rd_horseshoe.py` (21 tests). Numbers: `python docs/measure_rd_horseshoe.py`,
run from the repo root. Environment: Python 3.11.2, pandas 2.3.3, numpy 1.26.4. Measured
2026-11-25.

## Decisions

1. **Bar numbering.** The issue's "bar 1..4" are read oldest to newest, with bar 4 the
   current bar: bar1 = `T-3` (`.shift(3)`), bar2 = `T-2`, bar3 = `T-1`, bar4 = `T` (the
   unshifted current bar). This matches the prototype's own indexing (`red.shift(3)` for
   bar1 down to the unshifted series for bar4) and is the only reading consistent with
   "bar 1" supplying `open1` for the outer-bound check and "bar 4" supplying `close4`.
2. **"Cannot be above both" kept as the issue's own reading**, `<= max(open1, close4)`
   for the bull case (mirrored `>= min(open1, close4)` for the bear lows) — this session
   does not re-derive it from the Reddit post, which is not re-fetched (no web access in
   this worktree). Disclosed in the issue text itself, carried through unchanged.
3. **A doji (close == open) is neither red nor green**, so it breaks either pattern at
   whichever bar it lands on. Not stated by the poster, but the only reading consistent
   with "red" and "green" being mutually exclusive, binary classifications of a candle
   (`tests/test_rd_horseshoe.py::test_a_doji_breaks_the_colour_requirement`).
4. **Both middle-bar bound checks (`high.shift(2)` AND `high.shift(1)`, resp.
   `low.shift(2)` AND `low.shift(1)`) are required, not just one** — the issue says
   "highs of bars 2-3", plural, and the prototype ANDs both. Breaking either one blocks
   the fire (`test_outer_bound_violation_blocks_the_bull_pattern`,
   `test_outer_bound_violation_blocks_the_bear_pattern`).
5. **Shift-then-fill-False, not shift-then-NaN-then-AND.** `red`/`green` are plain bool
   Series; `Series.shift(n, fill_value=False)` keeps them bool-dtype through the shift
   (no object-dtype/NaN detour), so the four-bar AND chain never has to reason about
   `bool & NaN`. The final output is masked to NaN for the 3-bar warm-up afterward via
   `.where(bar1_open.notna())`, so the fill-False choice cannot manufacture a false
   fire in the warm-up — it only affects bars where the chain's other four-AND terms
   already determine the answer.
6. **Column is `RD_HORSESHOE`, no parameters** — the formation is fixed at 4 bars by the
   poster's own definition, so there is nothing to name a default against (unlike
   `CDL_DOJI_10_0.1`'s `length`/`factor`).
7. **A NaN anywhere in the 4-bar window reads 0, not NaN** — only the 3-bar warm-up is
   masked (`.where(bar1_open.notna())`); a NaN in `high`/`low`/`close` inside the window
   makes every comparison `False`, so the bar reports "formation absent" rather than
   "unknown". Unreached on the Gate E data: the non-NaN deficit is 267 = 3 × 89 frames,
   warm-up only. Would understate NaN on a gappy frame.

## Gate A — correctness

The issue's own formula (not the prototype — issue #164's explicit instruction), read
bar-by-bar in the module's docstring:

```
red   = close < open
green = close > open
BULL: bar1 red, bar2 green, bar3 red, bar4 green,
      high(bar2) <= max(open(bar1), close(bar4)), high(bar3) <= max(open(bar1), close(bar4))
BEAR: bar1 green, bar2 red, bar3 green, bar4 red,
      low(bar2) >= min(open(bar1), close(bar4)), low(bar3) >= min(open(bar1), close(bar4))
RD_HORSESHOE = +1 if BULL, -1 if BEAR, 0 otherwise
```

Two hand-derived fixtures, every input bar and the expected output chosen on paper
before the module ran (`tests/test_rd_horseshoe.py::test_bull_fixture_is_exact`,
`test_bear_fixture_is_exact`):

| fixture | bars (O/H/L/C) | outer bound | result |
|---|---|---|---|
| bull | (100,101,97,98) (98,100.7,97.8,100.5) (100.5,100.9,98.5,99) (99,101.6,98.7,101) | `max(100, 101) = 101`; highs 100.7, 100.9 both `<= 101` | `+1.0` at bar 4 |
| bear | (100,103,99.5,102) (102,102.3,99.3,100) (100,101.8,99.8,101.5) (101.5,101.7,98.5,99) | `min(100, 99) = 99`; lows 99.3, 99.8 both `>= 99` | `-1.0` at bar 4 |

Two gating fixtures confirm the outer-bound check is load-bearing, not decorative:
pushing the bull fixture's bar2 high to 101.2 (above the 101 bound) drops the result to
`0.0`; pushing the bear fixture's bar2 low to 98.7 (below the 99 bound) does the same
(`test_outer_bound_violation_blocks_the_bull_pattern`,
`test_outer_bound_violation_blocks_the_bear_pattern`). A third fixture confirms a doji
(bar3 close forced equal to its own open) breaks the bull pattern even though the
outer-bound check alone would pass (`test_a_doji_breaks_the_colour_requirement`).

## Gate B — causality

- **The real module never reads the future, swept, not spot-checked.** Two 600-bar
  synthetic frames (seeds 1 and 2) spliced at `J`: bars `< J` come only from seed 1 in
  both the base and the spliced frame, so if the module reads no later bar than `T` its
  output on `[0, J)` cannot move. Measured over **293 swept J values** (`J` = 10, 12, ...,
  594, `python docs/measure_rd_horseshoe.py`): **real module leaked at 0 of 293**.
- **A single fixed J is a weak catch here, like `smc_sweep` (`tests/test_altport2_ports.py`).**
  The pattern fires on ~8% of settled bars (below), so a one-bar back-date only shows up
  when the bar adjacent to `J` happens to be an event. The mutant (the final write
  `horseshoe.where(bar1_open.notna())` with a `.shift(-1)` appended, reading one bar into
  the future) is live (differs from the real module on the unperturbed frame) and
  **leaked at 24 of the same 293 swept J values** — enough to prove it is caught, not
  enough to expect it at every J (`tests/test_rd_horseshoe.py::test_mutant_is_caught_across_a_sweep_of_perturbation_points`).

## Gate C — reachability

Real data, from the Gate E run (`is164-rd_horseshoe-4232c7c2`, 89 ALTPORT-1 BIST frames,
398,849 pooled bars): `RD_HORSESHOE` is non-NaN on 398,582 of the pooled cells and
non-zero (fires, either sign) on 13,290 of those — both bounded away from 0 and from
`n`, so not constant on real data either.

Synthetic, from this session (no real-data cache in this worktree when this section was
first written):

- **2,000-bar frame (seed 4):** 1,997 of 2,000 bars fire (3-bar warm-up); **79 bull, 84
  bear, 1,834 at zero** — both signs reachable, and the column is not constant
  (`tests/test_rd_horseshoe.py::test_fires_both_signs_and_is_not_constant`).
- **10 independent 600-bar frames (seeds 100–109):** bull counts 14–26, bear counts
  13–25 per frame — both signs fire on every one of the 10 frames, not just the frame
  the reachability test happens to use.
- What blanks a bar: the 3-bar warm-up (no full 4-bar window); nothing else, since every
  input bar after that is a valid OHLC quadruple by construction.

## Gate D — scale-free

- x8, x64 (power-of-two), and x10, x3.7 (not powers of two): **bit-identical, 0
  mismatches on 597 co-finite cells** at every one of the four factors
  (`tests/test_rd_horseshoe.py::test_price_scale_is_bit_identical`,
  `python docs/measure_rd_horseshoe.py`). Unlike a continuous-magnitude column, there is
  no tolerance band to report separately for the non-power-of-two factors: every term in
  the chain is a comparison (`<`, `>`, `<=`, `>=`) or an `np.maximum`/`np.minimum` pick
  between two like-for-like price terms, so a positive rescale preserves every
  comparison's truth value exactly, not merely approximately.
- `0 < fires < n`, and the column is not constant: 163 of 1,997 settled bars fire on the
  2,000-bar frame above, both signs present.

## Gate E — attribution

Run `is164-rd_horseshoe-4232c7c2` (`gate_e_overlap.py run --module
pandas_ta.candles.rd_horseshoe`), 89 ALTPORT-1 BIST frames, 687 comparators (329
`compute_all` + 358 `ml_features` manifest), canary bit-equal on AKBNK.IS, BIENY.IS,
AGHOL.IS, SASA.IS. Recorded in `docs/gate_e_ledger.csv` (measured 2026-11-25).

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---|---|---|---|---|
| `RD_HORSESHOE` | 0.2168 | `VOL_DELTA_APPROX` (compute_all) | 397,171 | 0.2248 | SHIP |

0.2168 < 0.76 (SHIP band, `r3-perframe-0.90`): not struck, not disclosed, ships as-is.
Next comparators: `bop` (compute_all) 0.2151, `bop_Pctl` (manifest) 0.2099, n 393,598. 0 degenerate comparators;
398,582 non-NaN of the pooled cells, 13,290 non-zero.

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole suite):

```
python -m pytest -q tests/test_rd_horseshoe.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

**1,551 passed, 7 skipped** (re-run 2026-11-25 after the Gate E ledger row above was
recorded — the prior round's one expected failure,
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, is now green).
`tests/test_rd_horseshoe.py` alone: 21 passed.

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in for a GitHub
runner without AVX-512 — the four features issue-solver's rules name, not this machine's
full dispatchable set, which also has `AVX512CD`/`AVX512_CLX`/`AVX512_CNL`/`AVX512_ICL`
enabled): `python docs/measure_rd_horseshoe_cpu.py` — **21 passed** (just
`tests/test_rd_horseshoe.py`; the ledger/readme/wiring modules above are not
CPU-sensitive and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 392 → 393 (`tests/test_altport2_ports.py`).
- README: 392 → 393 registered, 400 → 401 callable, candles (5) → (6).
- `docs/MLCompanionContract.md`: 737 → 738 tagged and 104 → 105 `BIN` (newest first in
  the chain). `RD_HORSESHOE` tags `BIN` because the output is a discrete `{-1, 0, 1}`
  flag, not a continuous magnitude — the dictionary generator's own probe frame confirms
  it (`docs/IndicatorDictionary.md`'s `rd_horseshoe` row), not merely asserted here.
- `docs/IndicatorDictionary.md`, regenerated with this environment's package. Its diff is
  the `rd_horseshoe` row (`RD_HORSESHOE` BIN, 3-bar warm-up), the three header counts, the
  candles section count, the BIN/ORD shortlist, and nothing else (checked:
  `git diff docs/IndicatorDictionary.md`).
- `Category`: `rd_horseshoe` is placed alphabetically last in `candles`, after `ha`.
