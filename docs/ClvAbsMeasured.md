# Mean absolute close location (14) — measured (`clv_abs`)

Issue #200 (B3-CLV-ABS-14), from the 2026-10-29 ResearchIntel Reddit-KB scan, batch 3
(round 9, `docs/issues/screen/candidates_r9.csv`). Crowd talk (Reddit, tier 4): the
definition comes from a post or comment, and nothing in this port tests what the poster
says it does — existence, not evidence.

**Source:** Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:TradingView:1gofmli
(2024-11-11) https://www.reddit.com/r/TradingView/comments/1gofmli/ — the poster's words:
"float volume_strength = ta.sma(math.abs(volume_pressure), length_sma)". Claimed use:
scales the momentum signal by how one-sided volume pressure has been — **not
independently tested here.** The issue gives the formula
(`strength = SMA14(|vp|), vp = (buy - sell) / (buy + sell) = 2*CLV - 1`), not the whole
script, so there is no source line number to cite. Gate A below reads the formula from
the issue's own statement (its own instruction: "Gate A starts from the source formula,
not the prototype"), not from the screen prototype
(`docs/issues/screen/ind_screen_r9.py`'s `b3_clv_abs_14`).

**Status:** Gates A–D measured, wiring and tests in place. **Gate E SHIP**, 0.1778 vs
`ROLLING_LOW_250` (owner's run `pr401-clv_abs` at merge time, 2026-11-26, recorded in
`docs/gate_e_ledger.csv`). Review round 1 (`docs/reviews/2026-11-25-clv-abs-review.md`) changed the
zero-range rule (Decision 2). Every number below is from the re-run after that change.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/candles/clv_abs.py` | candles | `CLVABS_14` | `[0, 1]` when `low <= close <= high`, or NaN |

Tests: `tests/test_clv_abs.py` (26 tests). Numbers: `python docs/measure_clv_abs.py`, run
from the repo root (a few minutes, mostly the fork-overlap sweep). Environment: Python
3.11.18, pandas 2.3.3, numpy 1.26.4. Measured 2026-11-25.

## Decisions

1. **No volume is read, despite the name.** The poster calls `vp` "volume pressure", but
   `buy = close - low` and `sell = high - close` are price distances, and the issue's own
   identity `vp = 2*CLV - 1` confirms it. The module takes `high`, `low`, `close` only.
   That is why it lives in `candles`, not `volume`.
2. **A zero-range bar (`high == low`) is skipped, not propagated (round 1).**
   `buy + sell = high - low = 0` makes `vp` 0 / 0, which is NaN here and `na` in Pine. The
   source then feeds `|vp|` to `ta.sma`. The Pine v5/v6 reference's Remarks for `ta.sma`
   read: "`na` values in the `source` series are ignored; the function calculates on the
   `length` quantity of non-`na` values." **That sentence is recalled, not fetched.** The
   reviewer and the porter both recalled it, but WebFetch was refused in this session, so
   the owner should confirm it at
   https://www.tradingview.com/pine-script-reference/v6/#fun_ta.sma. The port follows it:
   `|vp|.dropna().rolling(length).mean()`, reindexed and forward-filled. On a flat bar
   the output therefore equals the prior bar's, and the next windows reach back past it.
   Round 0 instead let one flat bar blank `length` outputs. Nothing in the repo supported
   that rule. It cost 504 of 2,000 bars on the seed-4 frame; the skip rule leaves 14
   unsettled bars on that frame (Gate C).
   `test_zero_range_bar_is_skipped_not_propagated_nor_zeroed` tells the readings apart:
   skip → 0.875, propagate → NaN, flat-as-zero → 0.625.
3. **Simple mean, not Wilder/EMA:** `ta.sma` in the source.
4. **Column is `CLVABS_14`.** The length is the only parameter, and the name encodes it
   (`CLVABS_5` at `length=5`).
5. **The range is `[0, 1]` only on valid bars.** If close lies outside `[low, high]` (bad
   data), `|vp|` exceeds 1. That case is not clipped; the docstring states it.

## Gate A — correctness

The issue's formula, read bar by bar in the module docstring:

```
buy  = close - low
sell = high - close
vp   = (buy - sell) / (buy + sell)      NaN when high == low
CLVABS_14 = mean of the last 14 non-NaN |vp| (Pine ta.sma skips na)
```

Hand-derived fixtures (length 4, `python docs/measure_clv_abs.py`):

| fixture | bars (H/L/C) | result |
|---|---|---|
| close_at_extreme | (102, 98, 102) (101, 99, 99) ×2 | bar 3 `1.0`: every close at the high or the low |
| mid_range | (102, 98, 100) ×4 | bar 3 `0.0`: every close at mid-range |
| mixed | closes 101, 100, 98, 99 in [98, 102] | bar 3 `0.5`: \|vp\| = 0.5, 0, 1, 0.5 |
| zero_range | \|vp\| 0.5, 0, 1, 0.5, 1, *flat*, 1 | bars 3..6 = `0.5, 0.625, 0.625, 0.875` |

Independent reference: `tests/test_clv_abs.py::_reference` is a per-bar loop in plain
Python floats, with no pandas rolling. It keeps the non-NaN `|vp|` seen so far and
averages the last `length` of them, following the `ta.sma` sentence above rather than
the module's code. It is compared with the module on tick-rounded 2,000-bar frames
(tick 0.05, about 2% flat bars):

| seed | zero-range bars | length 5: settled / max abs diff | length 14: settled / max abs diff |
|---|---|---|---|
| 1 | 50 | 1,996 / 4.44e-16 | 1,987 / 2.78e-16 |
| 2 | 64 | 1,996 / 6.66e-16 | 1,986 / 2.22e-16 |
| 3 | 38 | 1,996 / 4.44e-16 | 1,987 / 1.67e-16 |

The NaN masks are identical in all six cases.

## Gate B — causality

- **The real module never reads the future, swept, not spot-checked.** Two 600-bar
  frames (seeds 1 and 2) are spliced at `J`, over **293 swept J values** (`J` = 10, 12,
  ..., 594). Without flat bars, the **real module leaked at 0 of 293**. With 2% flat bars,
  which drives the dropna → rolling → reindex → ffill path, it also **leaked at 0 of 293**.
- **The mutant** shifts the `|vp|` write one bar earlier (`vp_abs = vp.abs()` →
  `vp.abs().shift(-1)`, so the mean reads one bar ahead). It is live: it differs from the
  real module on the unperturbed frame. It **leaked at 285 of the same 293 J values**
  (no-flat frames, `test_mutant_is_live_and_caught`).

## Gate C — reachability

Synthetic only. This worktree has no real-data cache; the real-data count comes with the
Gate E run.

- **2,000-bar frame (seed 4, 42 zero-range bars):** 1,986 of 2,000 bars settled, all
  1,986 non-zero, 1,928 distinct values, range 0.1224–0.6602 (median 0.3222). The 14
  unsettled bars are the 13-bar warm-up plus one bar, because a flat bar falls inside
  the warm-up. All counts are pinned in `test_reachability_counts`.
- **10 independent 600-bar frames (seeds 100–109):** 585–587 settled bars per frame,
  558–573 distinct values each, minimum 0.1160 and maximum 0.6449 across them. The column
  is not constant on any of the 10.

## Gate D — scale-free

2,000-bar frame, seed 4, 1,986 co-finite cells:

| factor | NaN masks equal | mismatches | max abs diff |
|---|---|---|---|
| ×8 | yes | 0 | 0 |
| ×64 | yes | 0 | 0 |
| ×10 | yes | 1,978 | 1.94e-14 |
| ×3.7 | yes | 1,980 | 1.79e-14 |

×10 and ×3.7 differ only in the last bits (rolling-sum rounding of `|vp|` values that are
already rounded differently). The test tolerance is 1e-12. `0 < fires < n`: 1,986
non-zero settled bars of 2,000, not constant (`test_scale_fires_and_is_not_constant`).

## Gate E — attribution

**SHIP.** Run `pr401-clv_abs` (2026-11-26, at merge time; not printed by
`docs/measure_clv_abs.py`), 89 BIST frames, 687 comparators, recorded in `docs/gate_e_ledger.csv`.

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---:|---|---:|---:|---|
| `CLVABS_14` | 0.1778 | `ROLLING_LOW_250` (compute_all) | 376,599 | 0.2173 (`ZIGZAG`) | SHIP |

Next comparators: `ZIGZAG` 0.1772 (n = 33,636), `ROLLING_HIGH_250` 0.1758. Real-data reach:
397,621 non-NaN bars pooled, all non-zero.

For orientation, the earlier numbers that were not this port's Gate E:

- The issue's prototype run (`screen_r9_20261029`) measured max |ρ| 0.1851 vs `ZIGZAG`
  (n = 32,580), with a top-5 per-frame max median of 0.2087. The prototype's na rule is
  not known here, because its file is on the owner's machine only.
- **Fork overlap, `fork_overlap()` in `docs/measure_clv_abs.py`:** 14 synthetic
  1,500-bar frames (ticks 0.01/0.05/0.1, Student-t(4) returns with volatility regimes,
  871 zero-range bars, 19,600 candidate rows after bar 100), against 559 comparator
  columns from every other `Category` indicator at defaults. Highest per-frame median
  |ρ| values: **0.2269** vs `range_profile`'s `RPO_VA_WIDTH_PCT_110_80`, then 0.2212
  `G191_093_20`, 0.2168 `LEVELSHIFTSIZE_100`, 0.2090 `GKVOL_20` and 0.2045 `STLSPIKE_100`.
  The pre-port equivalence check reported 0.2770 against the same top column, but that
  was measured on round 0's na-propagating candidate and had no reproducing script. It is
  superseded by these numbers.

## Gate F — suites

This session's own command (the full suite is run once by the orchestrator):

```
python -m pytest -q -x --tb=short -p no:cacheprovider -W ignore tests/test_clv_abs.py \
    tests/test_altport2_ports.py tests/test_gate_e_ledger.py \
    tests/test_indicator_list_tables.py tests/test_readme_counts.py \
    tests/test_ml_companions.py tests/test_wiring_accessors.py
```

Re-measured after round 1: **1,551 passed, 8 skipped, 0 failed**. One of the skips is
`clv_abs`'s "Gate E owed". `tests/test_clv_abs.py` alone: 26 passed.

## Counters touched

- `Category`: `clv_abs` is placed alphabetically in `candles`, after `cdl_z`, and its
  import sits in the same place in `pandas_ta/candles/__init__.py`.
- `CATEGORY_TOTAL` 397 → 398 (`tests/test_altport2_ports.py`).
- README: 397 → 398 registered, 405 → 406 callable, candles (7) → (8). The counts were
  read back from the package (`sum(len(v) for v in ta.Category.values())` = 398) and
  from the regenerated dictionary.
- `docs/MLCompanionContract.md`: 742 → 743 tagged and 372 → 373 `SF`. The dictionary
  generator's probe tags `CLVABS_14` `SF` with a 13-bar warm-up.
- `docs/IndicatorDictionary.md`, regenerated after round 1. Its diff is the `clv_abs`
  row, the three header counts, the candles section count and the scale-free name list.
