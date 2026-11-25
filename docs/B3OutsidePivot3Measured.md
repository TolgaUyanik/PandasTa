# 3-bar outside pivot: the prior bar is both swing high and swing low — measured (`b3_outside_pivot3`)

Issue #199 (B3-OUTSIDE-PIVOT3), from the 2026-10-29 ResearchIntel Reddit-KB scan,
batch 3 / round 9 (`docs/issues/screen/candidates_r9.csv`). Crowd talk (Reddit, tier 4):
the definition comes from a post or comment, and nothing in this port tests what the
poster says it does — existence, not evidence.

**Source:** Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:options:1k1hyso (2025-04-17)
https://www.reddit.com/r/options/comments/1k1hyso/ — the poster's words: "when a middle
candle's high is higher than the highs of 2 candles surrounding it, and also when the
middle candle's low is lower than the lows of 2 candles surrounding it". Claimed use:
exclude double-sided swings as unreliable swing signals — **not independently tested
here.** The issue gives the formula
(`high[t-1] > max(high[t-2], high[t]) AND low[t-1] < min(low[t-2], low[t])`), not a
script, so there is no source line number to cite; Gate A reads the formula from the
issue's own statement, not from the screen prototype
(`docs/issues/screen/ind_screen_r9.py`'s `b3_outside_pivot3`).

**Status:** Gates A–D measured, wiring and tests in place. **Gate E owed** (no ledger
row; `tests/test_gate_e_ledger.py` reports it as a "Gate E owed" skip on the way to
`dev`).

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/candles/b3_outside_pivot3.py` | candles | `B3_OUTSIDE_PIVOT3` | `{0.0, 1.0}` or NaN |

Tests: `tests/test_b3_outside_pivot3.py` (33 tests). Numbers:
`python docs/measure_b3_outside_pivot3.py`, run from the repo root. Environment:
Python 3.11.18, pandas 2.3.3, numpy 1.26.4. Measured 2026-11-25.

## Decisions

1. **Written on bar T, not on the middle bar T-1.** The pattern needs the right-hand
   neighbour (bar T) to exist, so the flag lands on the first bar at which it is
   knowable. Back-dating it onto T-1 reads one bar of future — that is exactly the
   Gate B mutant.
2. **Strict on both sides, both neighbours.** A tie of the middle bar's high (or low)
   with either neighbour does not fire, as the issue's `>`/`<` state. Four tie
   fixtures (left/right × high/low) pin it.
3. **Unsigned `{0, 1}`.** Open and close play no part in the formula and are not read.
4. **Not a restatement of a shipped column.** Read in the code, the flag is exactly
   `rd_outside_bar(high, low).shift(1)` AND `cdl_inside(asbool=True)` at T, but neither
   is shipped in that lagged, joined form. Measured by `decomposition()` in
   `docs/measure_b3_outside_pivot3.py` (synthetic frames, not Gate E): 14 tick-rounded
   OHLC frames × 2,000 bars (ticks 0.01/0.05/0.1, Student-t(4) returns, volatility
   regimes, 1,689 equal-high/equal-low ties, 48–97 fires per frame), 26,600 rows after a
   100-bar burn-in. The decomposition gave **0 mismatches** on every frame. Per-frame
   median Spearman ρ: **0.4528** against `CDL_INSIDE` (min 0.4106, max 0.5108), the best
   single shipped column, and **−0.0857** against `RD_OUTSIDE_BAR` at the same bar (min
   −0.1046, max −0.0568).
5. **Column is `B3_OUTSIDE_PIVOT3`, no parameters**, because the window is fixed at 3
   bars by the source's definition.
6. **Two warm-up NaN bars**, masked via `.where(left_high.notna())`.

## Gate A — correctness

```
B3_OUTSIDE_PIVOT3[T] = 1 IF high[T-1] > max(high[T-2], high[T])
                         AND low[T-1] < min(low[T-2], low[T])
                       ELSE 0
```

Hand-derived fixtures, value at bar 2 (two warm-up NaN bars in every case):

| fixture | bars (H/L) | result |
|---|---|---|
| fires | (101, 99) (102, 98) (101.5, 98.5) | `1.0` |
| swing_high_only | (101, 99) (102, 98) (101.5, 97) | `0.0` |
| swing_low_only | (101, 99) (102, 98) (103, 98.5) | `0.0` |
| left_high_tie | (102, 99) (102, 98) (101.5, 98.5) | `0.0` |
| left_low_tie | (101, 98) (102, 98) (101.5, 98.5) | `0.0` |
| right_high_tie | (101, 99) (102, 98) (102, 98.5) | `0.0` |
| right_low_tie | (101, 99) (102, 98) (101.5, 98) | `0.0` |

Independent reference: a pure-Python bar loop read straight from the formula (no pandas
shifts), on 12 tick-rounded frames × 1,500 bars at tick 1.0: **0 mismatches on every
frame**, with 646–753 equal-high/equal-low ties and 7–17 fires per frame
(`test_matches_independent_loop_on_tick_rounded_frames`).

## Gate B — causality

- Two 600-bar synthetic frames (seeds 1, 2) spliced at `J`, swept over **293 J values**
  (`J` = 10, 12, …, 594): **real module leaked at 0 of 293**.
- Mutant: the final write with `.shift(-1)` appended (flag back-dated onto the middle
  bar). It is live (differs from the real module on the unperturbed frame) and **leaked
  at 12 of the same 293 J values**. The pattern is rare (Gate C), so a one-bar back-date
  only shows when an event sits next to J. The test therefore asserts "some J", not
  "every J".

## Gate C — reachability

Synthetic only (no real-data cache in this worktree; the real-data count comes with the
Gate E run):

- **2,000-bar frame (seed 4):** 1,998 settled bars (2-bar warm-up); **69 fire, 1,929 at
  zero**.
- **10 independent 600-bar frames (seeds 100–109):** 10–22 fires of 598 settled bars
  per frame. It fires on every frame.
- Nothing blanks a bar after the 2-bar warm-up.

## Gate D — scale-free

- ×8, ×64, ×10, ×3.7 on the 2,000-bar seed-4 frame: NaN masks equal, **0 mismatches on
  1,998 co-finite cells** at each factor. All four are bit-identical, because every
  comparison is between like-for-like price terms.
- `0 < fires < n`: 69 of 1,998.

## Gate E — attribution

**Owed.** Not run in this session (private engine and cache). The prototype's screen
number from the issue (`screen_r9_20261029`, max |ρ| 0.1318 vs `HIGHER_HIGH`,
n = 398,671) is a prototype measurement, not this module's, and is not recorded in the
ledger. Module sha1 (LF-normalised) at the time of this receipt:
`5a14f7e6194fff4b8f6fe3028b6d4180fbb18359`.

## Gate F — suites

This session's targeted command (not the full suite):

```
python -m pytest -q -x --tb=short -p no:cacheprovider -W ignore tests/test_b3_outside_pivot3.py \
    tests/test_altport2_ports.py tests/test_gate_e_ledger.py tests/test_indicator_list_tables.py \
    tests/test_readme_counts.py tests/test_ml_companions.py tests/test_wiring_accessors.py
```

**1,558 passed, 8 skipped, 0 failed** (one of the skips is the "Gate E owed" for
`b3_outside_pivot3`). `tests/test_b3_outside_pivot3.py` alone: 33 passed.

The full PandasTa suite and the Backtesting suite are owed with Gate E. Neither was run in
this session.

## Counters touched

- `CATEGORY_TOTAL` 397 → 398 (`tests/test_altport2_ports.py`).
- README: 397 → 398 registered, 405 → 406 callable, candles (7) → (8). All read back
  from the package.
- `docs/MLCompanionContract.md`: 742 → 743 tagged and 106 → 107 `BIN`, recounted from the
  regenerated dictionary.
- `docs/IndicatorDictionary.md` regenerated. Its diff is the probed/registered/callable
  header counts, the candles section count, the new `b3_outside_pivot3` row
  (`B3_OUTSIDE_PIVOT3` BIN, 2-bar warm-up), and the BIN/ORD shortlist.
- `Category`: `b3_outside_pivot3` placed alphabetically first in `candles`.
