# Short over long average of the 5-bar high-low spread (10, 50) — measured (`rd_range_contraction`)

Issue #176 (RD-RANGE-CONTRACTION), from the 2026-10-25 ResearchIntel Reddit-KB scan, round 6
(`docs/issues/screen/candidates_r6.csv`). Crowd talk (Reddit, tier 4): the definition comes
from a post or comment, and nothing in this port tests what the poster says it does —
existence, not evidence.

**Source:** Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:dejh73 (2019-10-07)
https://www.reddit.com/r/algotrading/comments/dejh73/ — the poster's words: "look for a long
period MA of your spread measurement to cross over a short period MA of your spread
measurement." Claimed use: Wedge detection component (converging range) — **not independently
tested here.** A Reddit post is not a script, so there is no source line number to cite; Gate A
below reads the formula directly from the issue's own restatement (its own instruction: "Gate A
starts from the source formula, not the prototype"), not from the screen prototype
(`docs/issues/screen/ind_screen_r6.py`'s `rd_range_contraction`, which is mathematically the same
reading but is not what Gate A cites). `n=5` (the spread window) and `short=10`/`long=50` (the two
MA windows) are not in the poster's words — the issue discloses all three as the prototype's own
choice ("n = 5, MAs 10 and 50, as a ratio"), kept here as parameters, not hard-coded.

**Status:** Gates A-D measured below. Gate E and the whole-suite run are owed, per the
issue-solver's own rules (it must not run `../Backtesting` or the whole suite).

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/volatility/rd_range_contraction.py` | volatility | `RD_RANGE_CONTRACTION_5_10_50` | continuous, > 0 (ratio of two positive averages of a non-negative spread); measured 0.520985..1.461548 on a 1,200-bar synthetic frame below; NaN during warm-up or where the long-window average spread is exactly zero |

Tests: `tests/test_rd_range_contraction.py` (21 tests). Numbers: `python
docs/measure_rd_range_contraction.py`, run from the repo root. Environment: Python 3.11.2,
pandas 2.3.3, numpy 1.26.4. Measured 2026-11-26.

## Decisions

1. **Ratio, not "cross over."** The poster's words describe a crossover signal ("a long period
   MA... to cross over a short period MA"), but the issue's own "Prototype" line states the
   scale-free form as a ratio of the two MAs ("as a ratio"), not a crossover flag — a continuous
   ratio is both a superset of the crossover information (the sign of `ratio - 1` is the
   crossover) and a better-shaped ML feature (continuous, not a sparse event). This port ships
   the issue's own scale-free form, `MA(spread, short) / MA(spread, long)`, matching the screen
   prototype's `sdiv(mean(s, 10), mean(s, 50))`.
2. **`n`, `short`, `long` are parameters, not hard-coded** — same convention as every other
   `rd_*` port in this fork (e.g. `rd_knot_dslope_40`'s `length`/`knot_margin`): the issue's
   defaults (5, 10, 50) are kept as the module's own defaults, but the shape generalises.
3. **`short`/`long` are swapped if given backwards** (`if long < short: short, long = long,
   short`), same guard `massi` uses for its own `fast`/`slow` — so `rd_range_contraction(h, l,
   short=50, long=10)` returns the identical column as the defaults, not a silently inverted
   ratio (`tests/test_rd_range_contraction.py::test_short_and_long_are_swapped_if_given_backwards`).
4. **A zero long-window average reads NaN, not ±inf** — a dead market with a constant (or
   all-zero) 5-bar spread makes the long MA exactly 0, and `0/0` or `x/0` would otherwise be NaN
   or ±inf depending on the numerator; `sdiv`'s own convention (replace ±inf with NaN) is
   reproduced directly rather than imported, since this module has no other dependency on
   `docs/issues/screen/ind_screen.py` (a gitignored, non-shipped file).
5. **Rolling mean is a plain `pandas.Series.rolling(n).mean()`**, matching the screen
   prototype's `mean()` helper — the poster leaves the MA type open ("a long period MA... a
   short period MA"), and the prototype's SMA choice is adopted as stated by the issue's own
   "Prototype" line, not re-derived.
6. **Column name carries all three parameters**, `RD_RANGE_CONTRACTION_{n}_{short}_{long}` —
   e.g. `RD_RANGE_CONTRACTION_5_10_50` at defaults, `RD_RANGE_CONTRACTION_3_5_20` at
   `n=3, short=5, long=20`.

## Gate A — correctness

The issue's own formula (not the prototype — issue #176's explicit instruction), read bar-by-bar
in the module's docstring:

```
spread_t = HHV(high, n)_t - LLV(low, n)_t
RD_RANGE_CONTRACTION_t = MA(spread, short)_t / MA(spread, long)_t
```
with `n=5, short=10, long=50`; `MA` is a simple rolling mean; division by zero → NaN.

A hand-derived fixture, chosen on paper before the module ran
(`tests/test_rd_range_contraction.py::test_hand_derived_value`): a flat `high=11/low=9` (spread
2) for 5 bars then a step to `high=21/low=9` (spread 12) for 3 more, at `n=2, short=2, long=4`.
At bar 7 the spread series is `[nan,2,2,2,2,12,12,12]`, so `short_MA = mean(12,12) = 12` and
`long_MA = mean(2,12,12,12) = 9.5`; the module's output is `12/9.5 = 1.263157894736842`, matching
to the bit (`python docs/measure_rd_range_contraction.py`).

Cross-checked against an independent per-window Python loop built straight from the formula
above (plain `numpy.lib.stride_tricks.sliding_window_view` + `np.max`/`np.min`/`.mean()`, not
pandas `.rolling`, and not read from the module) on a 400-bar synthetic OHLC random walk
(n=5, short=10, long=50, 347 defined bars): NaN masks identical, **max |diff| 6.661e-16**
(`test_matches_an_independent_loop`, `python docs/measure_rd_range_contraction.py`) — float
noise from the two different reduction orders (pandas `.rolling().mean()` vs. a Python-level
mean over a numpy slice), not a logic mismatch.

## Gate B — causality

- **The real module never reads the future, swept, not spot-checked.** Two 1,200-bar synthetic
  OHLC walks (seeds 1 and 2) spliced at `J`: bars `< J` come only from seed 1 in both the base
  and the spliced series, so if the module reads no later bar than `T` its output on `[0, J)`
  cannot move. Measured over **25 swept J values** (`J` = 100, 140, ..., 1060, past the 53-bar
  default warm-up; `python docs/measure_rd_range_contraction.py`): **real module leaked at 0 of
  25**.
- **The mutant (the final ratio assignment with a `.shift(-1)` appended, reading one bar into
  the future) is live** (differs from the real module on the unperturbed frame) **and leaked at
  25 of the same 25 swept J values** — every offset, since a one-bar shift of a continuous,
  almost-everywhere-changing ratio moves essentially every downstream bar
  (`tests/test_rd_range_contraction.py::test_lookahead_mutant_is_caught`).

## Gate C — reachability

Synthetic, from the port session:

- **1,200-bar frame (seed 4):** 1,147 of 1,200 bars fire (53-bar warm-up); values range
  **0.520985 to 1.461548** across **1,147 distinct values** — straddling 1.0 (both a
  contracting range, ratio < 1, and an expanding one, ratio > 1, are reachable), never negative
  or zero (a ratio of two sums of a non-negative spread).
- **10 independent 600-bar frames (seeds 100-109):** every frame fires on 547 of 600 bars (the
  fixed 53-bar warm-up) and reads 547 distinct values; every seed's range sits inside
  roughly [0.55, 1.61] — consistent with the single-frame figures above, not an outlier.
- **A zero long-window average reads NaN by construction**
  (`test_zero_long_average_reads_nan_not_inf`); not observed on the random synthetic frames
  above (a GBM-style walk's spread is never exactly constant for 50 bars), which is expected,
  not a defect.
- **Real-data reachability**: not measured here — Gate E (which runs on real BIST data) is
  owed; see below.

## Gate D — scale-free

- **Bit-identical under a power-of-two price rescale (x8/x64), tolerance under any other
  (x10/x3.7).** For an exactly-representable rescale by `k`, `HHV(high*k, n) = k*HHV(high, n)`
  and `LLV(low*k, n) = k*LLV(low, n)` exactly — max/min select an existing window element rather
  than compute a new value, so scaling every element by the same exact factor scales the
  selected max/min by that same factor. `spread' = k*HHV(high,n) - k*LLV(low,n)`, and because
  `k` is a power of two this subtraction is itself exact (no rounding is introduced scaling an
  IEEE-754 subtraction's operands by a common power-of-two factor), so `spread' = k*spread`
  bit-for-bit. The same argument carries through both rolling means (`MA(spread, short)` and
  `MA(spread, long)`): each is exactly `k` times its unscaled counterpart. The final ratio is
  then IEEE-754 division of two operands both scaled by the identical exact `k`, which returns a
  bit-identical quotient to the unscaled division — the same cancellation `massi`
  (`pandas_ta/volatility/massi.py`, a ratio of two EMAs of the same high-low range) relies on. A
  non-power-of-two rescale (x10, x3.7) is not exact at the max/min-selection or subtraction
  steps, so that stays a tiny-tolerance claim.
- **Measured on the 1,200-bar seed-4 frame, 1,147 co-finite cells**
  (`python docs/measure_rd_range_contraction.py`):

  | k | exact mismatches | max abs diff | max rel diff |
  |---|---|---|---|
  | 8.0 | 0 | 0.0 | 0.0 |
  | 64.0 | 0 | 0.0 | 0.0 |
  | 10.0 | 1059 of 1147 | 3.553e-15 | 3.594e-15 |
  | 3.7 | 1054 of 1147 | 2.887e-15 | 3.224e-15 |

  x8/x64 are exact zero (`test_price_scale_is_bit_identical`, `==` comparison, not a tolerance).
  x10/x3.7 land near the float noise floor.
  `tests/test_rd_range_contraction.py::test_scale_stays_within_a_tiny_tolerance` bounds the
  x10/x3.7 case at `rtol=1e-9, atol=1e-9` — a generous margin above the measured figures, not
  the measured figures themselves, per the issue-solver's own CPU-variant rule (the exact last
  bit is the CPU's dispatched kernels' call, not this module's logic).
- `0 < fires < n`, not constant: 1,147 of 1,200 bars fire on the 1,200-bar frame above, 1,147
  distinct values, min 0.520985 and max 1.461548 (both sides of 1.0 reachable).

## Gate E — attribution

**Gate E: pending, run by issue-solver after this session.** This session cannot run `../Backtesting` or
the whole-suite harness (rule explicit in the issue-solver system prompt). The prototype's own
pre-flight measurement (`docs/issues/screen/ind_screen_r6.py`'s `rd_range_contraction`, same
formula, not re-derived here) is quoted verbatim in the issue: max |ρ| **0.7763** vs `massi`
(compute_all, n = 394,132), top-5 per-frame max median 0.7817 → **DISCLOSE** band. That number is
the PROTOTYPE's, run `screen_r6_20261025`; it is not a substitute for the port's own Gate E run,
which issue-solver's rules require but cannot execute in this session. To run it, from
`../Backtesting/Backtesting`:
`python scripts/analysis/gate_e_overlap.py run --module pandas_ta.volatility.rd_range_contraction --name rd_range_contraction`.
Module sha1 (LF-normalised, for `docs/gate_e_ledger.csv record`):
`6be70ac4c95f6f88a090ed5ec5dbcfed8d9f3978` (`python docs/measure_rd_range_contraction.py`).

If the re-run strikes the column (pooled |ρ| ≥ 0.90, or a top-5 comparator's per-frame median ≥
0.90), this is a **measured revert**: remove the module, its wiring and its tests, and keep this
file as the receipt — equally DONE as a ship, per the issue-solver's own rules.

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole suite):

```
python -m pytest -q tests/test_rd_range_contraction.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

**1,623 passed, 7 skipped, 1 failed.** The one failure is
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` — expected, per the
issue-solver's own rules, until the launcher's Gate E run and a later receipt session record
this port's ledger row. `tests/test_rd_range_contraction.py` alone: 21 passed.

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in for a GitHub runner
without AVX-512 — the four features issue-solver's rules name, not this machine's full
dispatchable set, which also has `AVX512CD`/`AVX512_CLX`/`AVX512_CNL`/`AVX512_ICL` enabled):
`python docs/measure_rd_range_contraction_cpu.py` — **21 passed** (just
`tests/test_rd_range_contraction.py`; the ledger/readme/wiring modules above are not
CPU-sensitive and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 402 → 403 (`tests/test_altport2_ports.py`); `CATEGORY_BUCKETS["volatility"]`
  39 → 40.
- README: 402 → 403 registered, 410 → 411 callable, volatility (39) → (40).
- `docs/MLCompanionContract.md`: 747 → 748 tagged and 376 → 377 `SF` (newest first in the
  chain). `RD_RANGE_CONTRACTION_5_10_50` tags `SF` because `spread` and its two moving averages
  all scale exactly with an exactly-representable price rescale, cancelling bit-identically in
  the ratio.
- `docs/IndicatorDictionary.md`, regenerated with this environment's package (`python
  docs/gen_indicator_dictionary.py`): adds `rd_range_contraction` under `## volatility (40)`,
  and the `SF` tag list.
- `Category`: `rd_range_contraction` is placed alphabetically between `range_profile` and
  `rogers_satchell` in `volatility`.
