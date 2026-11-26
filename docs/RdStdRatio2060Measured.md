# Price sd over its own 60-bar average (20) — measured (`rd_std_ratio_20_60`)

Issue #179 (RD-STD-RATIO-20-60), from the 2026-10-25 ResearchIntel Reddit-KB scan, round 6
(`docs/issues/screen/candidates_r6.csv`). Crowd talk (Reddit, tier 4): the definition comes
from a post or comment, and nothing in this port tests what the poster says it does —
existence, not evidence.

**Source:** Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:1lezs3n (2025-06-19)
https://www.reddit.com/r/algotrading/comments/1lezs3n/ — the poster's words: "normalized_vol =
price_std / avg_volatility." Claimed use: detect a flat/range market relative to its own recent
volatility — **not independently tested here.** A Reddit post is not a script, so there is no
source line number to cite; Gate A below reads the formula directly from the issue's own
restatement (its own instruction: "Gate A starts from the source formula, not the prototype"),
not from the screen prototype (`docs/issues/screen/ind_screen_r6.py`'s `rd_std_ratio_20_60`,
which is mathematically the same reading but is not what Gate A cites):
`normalized_vol = std(close, p) / mean(std(close, p), 3p)` with `p = 20`. `3p = 60` is the
issue's own substitution, not a judgment call — it is this candidate's own name.

**Status:** Gates A-E measured below. Gate E: DISCLOSE_GAP (0.8274 pooled, not STRUCK), ships.
Whole-suite run is owed to the launcher, per the issue-solver's own rules (it must not run the
whole suite).

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/volatility/rd_std_ratio_20_60.py` | volatility | `RD_STD_RATIO_20_60_20_60` | continuous, >= 0 (ratio of two non-negative stdevs); measured 0.254992..2.240932 on a 1,200-bar synthetic frame below; NaN during warm-up or where the average stdev is exactly zero |

Tests: `tests/test_rd_std_ratio_20_60.py` (20 tests). Numbers: `python
docs/measure_rd_std_ratio_20_60.py`, run from the repo root. Environment: Python 3.11.2,
pandas 2.3.3, numpy 1.26.4. Measured 2026-11-26.

## Decisions

1. **`length`/`avg_length` are parameters, not hard-coded** — same convention as every other
   `rd_*` port in this fork (e.g. `rd_obv_dev5`'s `length`/`vol_length`): the issue's own
   substitution (`p=20`, `3p=60`) is kept as the module's own defaults (`length=20,
   avg_length=60`), but the shape generalises, and `avg_length` does not auto-derive as
   `3 * length` when a caller overrides `length` alone (the same independent-parameter
   convention `rd_obv_dev5` used for its own `vol_length`).
2. **`std` is this fork's own `pandas_ta.statistics.stdev`** (pandas' rolling `.std()`, ddof=1
   by default). The poster's "price_std" names no convention beyond "std"; the screen
   prototype's own helper (`c.rolling(20).std()`, pandas default ddof=1) confirms ddof=1 as the
   intended reading, not ddof=0.
3. **`mean` is a plain rolling SMA** (`pandas_ta.overlap.sma`), matching both the prototype's
   `mean()` helper (`x.rolling(n).mean()`) and the issue's own `mean(std(close, p), 3p)` wording.
4. **A zero average stdev reads NaN, not ±inf** — a dead-flat market with zero stdev for
   `avg_length` consecutive bars makes the divisor exactly 0; `np.inf`/`-np.inf` are replaced
   with NaN explicitly, the same guard `rd_range_contraction` uses for its own zero-average
   case.
5. **Column name carries both parameters**, `RD_STD_RATIO_20_60_{length}_{avg_length}` — e.g.
   `RD_STD_RATIO_20_60_20_60` at defaults, `RD_STD_RATIO_20_60_10_30` at `length=10,
   avg_length=30`. The fixed `20_60` in the module/function name itself is the candidate's own
   name from the issue, kept as a literal suffix even though the parameters are not hard-coded
   (same convention as `rd_vwio_10`, `osap_retskew_21`).

## Gate A — correctness

The issue's own formula (not the prototype — issue #179's explicit instruction), read literally
in the module's docstring:

```
normalized_vol = std(close, p) / mean(std(close, p), 3p)
```
with `p=20` (`3p=60`); `std` is pandas' rolling stdev (ddof=1), `mean` a simple rolling mean;
division by zero → NaN.

A hand-derived fixture, chosen on paper before the module ran
(`tests/test_rd_std_ratio_20_60.py::test_hand_derived_value`): a flat `close=10.0` for 5 bars
then a step to `close=20.0` for 3 more, at `length=2, avg_length=4`. The 2-bar stdev series
(ddof=1) is `[nan, 0, 0, 0, 0, 10/sqrt(2), 0, 0]` — zero everywhere except the single step bar.
At bar 5 (0-indexed) the 4-bar average-of-stdev window is `[0, 0, 0, 10/sqrt(2)]`, mean
`(10/sqrt(2))/4`, so the ratio is `(10/sqrt(2)) / ((10/sqrt(2))/4) = 4.0` exactly on paper. The
module's measured output: **`bar5 = 4.0`** (`python docs/measure_rd_std_ratio_20_60.py`).

Cross-checked against an independent per-window Python loop built straight from the formula
above (plain `numpy.lib.stride_tricks.sliding_window_view` + `np.std(ddof=1)`/`.mean()`, not
pandas `.rolling`, and not read from the module) on a 400-bar synthetic close random walk
(length=20, avg_length=60, 322 defined bars): NaN masks identical, **max |diff| 1.249e-12**
(`test_matches_an_independent_loop`, `python docs/measure_rd_std_ratio_20_60.py`) — float noise
from the two different reduction orders (pandas `.rolling().std()`/`.mean()` vs. a Python-level
std/mean over a numpy slice), not a logic mismatch; well inside the test's own `atol=1e-9`
bound.

## Gate B — causality

- **The real module never reads the future, swept, not spot-checked.** Two 1,200-bar synthetic
  close random walks (seeds 1 and 2) spliced at `J`: bars `< J` come only from seed 1 in both
  the base and the spliced series, so if the module reads no later bar than `T` its output on
  `[0, J)` cannot move. Measured over **25 swept J values** (`J` = 200, 240, ..., 1160, past the
  78-bar default warm-up; `python docs/measure_rd_std_ratio_20_60.py`): **real module leaked at
  0 of 25**.
- **The mutant (the final ratio assignment with a `.shift(-1)` appended, reading one bar into
  the future) is live** (differs from the real module on the unperturbed frame) **and leaked at
  25 of the same 25 swept J values** — every offset, since a one-bar shift of a continuous,
  almost-everywhere-changing ratio moves essentially every downstream bar
  (`tests/test_rd_std_ratio_20_60.py::test_lookahead_mutant_is_caught`).

## Gate C — reachability

Synthetic, from the port session:

- **1,200-bar frame (seed 4):** 1,122 of 1,200 bars fire (78-bar warm-up); values range
  **0.254992 to 2.240932** across **1,122 distinct values** — straddling 1.0 (both a
  quieter-than-its-own-average and a noisier-than-its-own-average regime are reachable), never
  negative (a ratio of two non-negative stdevs).
- **10 independent 600-bar frames (seeds 100-109):** every frame fires on 522 of 600 bars (the
  fixed 78-bar warm-up) and reads 522 distinct values; every seed's range sits inside roughly
  [0.30, 2.97] — consistent with the single-frame figures above, not an outlier.
- **A zero average stdev reads NaN by construction**
  (`test_zero_average_stdev_reads_nan_not_inf`); not observed on the random synthetic frames
  above (a GBM-style walk's stdev is never exactly constant at 0 for 60 bars), which is
  expected, not a defect.
- **Real-data reachability**: not measured here — Gate E (which runs on real BIST data) is
  owed; see below.

## Gate D — scale-free

- **Bit-identical under a power-of-two price rescale (x8/x64), tolerance under any other
  (x10/x3.7).** For an exactly-representable rescale by `k`, pandas' rolling `.var()` computes
  a sum of squared deviations from the window mean divided by `(n - ddof)`; scaling every
  element of a window by the exact `k` scales every deviation by exactly `k` (subtraction of two
  exactly-k-scaled operands is itself exact for a power-of-two `k`), so each squared deviation
  scales by exactly `k**2` and their sum does too — `variance' = k**2 * variance` exactly, and
  `stdev' = sqrt(k**2 * variance) = k * stdev` exactly, since IEEE-754 `sqrt` is correctly
  rounded and a power-of-two `k` means `k * round(sqrt(variance))` and
  `round(sqrt(k**2 * variance))` are the same unique correctly-rounded value. `sma` of the
  now-`k`-scaled stdev series is linear (`SMA(k*x) = k*SMA(x)` exactly, same argument as the sum
  above), so the final ratio is IEEE-754 division of two operands both scaled by the identical
  exact `k`, which returns a bit-identical quotient to the unscaled division — the same
  cancellation `rd_range_contraction` (`pandas_ta/volatility/rd_range_contraction.py`) relies
  on for its own ratio of two rolling means. This relies on `pandas_ta/statistics/variance.py`
  computing `close.rolling(length, min_periods=...).var(ddof)` -- a deviation-FROM-THE-MEAN
  reduction -- rather than the naive `E[X**2] - E[X]**2` sum-of-squares form; the latter is the
  form `avwap_z` (`pandas_ta/volume/avwap_z.py`) documents losing precision on (catastrophic
  cancellation when the true variance is small relative to price**2), so that risk does not
  apply here. A non-power-of-two rescale (x10, x3.7) is not exact at the variance-sum or sqrt
  steps, so that stays a tiny-tolerance claim.
- **Measured on the 1,200-bar seed-4 frame, 1,122 co-finite cells**
  (`python docs/measure_rd_std_ratio_20_60.py`):

  | k | exact mismatches | max abs diff | max rel diff |
  |---|---|---|---|
  | 8.0 | 0 | 0.0 | 0.0 |
  | 64.0 | 0 | 0.0 | 0.0 |
  | 10.0 | 1122 of 1122 | 5.799e-12 | 9.149e-12 |
  | 3.7 | 1122 of 1122 | 4.920e-12 | 8.612e-12 |

  x8/x64 are exact zero (`test_price_scale_is_bit_identical`, `==` comparison, not a tolerance).
  x10/x3.7 land near the float noise floor.
  `tests/test_rd_std_ratio_20_60.py::test_scale_stays_within_a_tiny_tolerance` bounds the
  x10/x3.7 case at `rtol=1e-9, atol=1e-9` — a generous margin above the measured figures, not
  the measured figures themselves, per the issue-solver's own CPU-variant rule (the exact last
  bit is the CPU's dispatched kernels' call, not this module's logic).
- `0 < fires < n`, not constant: 1,122 of 1,200 bars fire on the 1,200-bar frame above, 1,122
  distinct values, min 0.254992 and max 2.240932 (both sides of 1.0 reachable).

## Gate E — attribution

**Measured** (launcher's run `is179-rd_std_ratio_20_60-f81ac76a`, `gate_e_overlap.py run
--module pandas_ta.volatility.rd_std_ratio_20_60`, 89 ALTPORT-1 frames, 398,849 pooled bars, 329
+ 358 = 687 comparators, canary bit-equal on AKBNK.IS/BIENY.IS/AGHOL.IS/SASA.IS):

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---|---|---|---|---|
| `RD_STD_RATIO_20_60_20_60` | 0.8273572620415864 | `BB_BWidth_Pctl` (manifest) | 391,907 | 0.8332215151007686 | **DISCLOSE_GAP** |

Next comparators: `CHOP` 0.7091109628127323 (compute_all), `BB_BWidth` 0.7001 (issue's own
prototype figure, not re-measured against this port directly). Matches the issue's own
prototype screen measurement (`screen_r6_20261025`) to four decimal places — this port is not a
new overlap, just the same formula re-measured on the shipped module.

Per `CLAUDE.md`'s Gate E bands (`r3-perframe-0.90`): STRUCK needs pooled \|ρ\| ≥ 0.90 or a
top-5 comparator's per-frame median ≥ 0.90. Neither holds (0.8274 pooled, 0.8332 per-frame
median), so this is **DISCLOSE_GAP, not STRUCK** — ships, disclosed, not reverted. Fork overlap
at stage 2 (not Gate E, scale-free `Category` outputs at defaults, 12 frames, from the port
session): max |ρ| 0.6675 vs `squeeze_pro:SQZPRO_OFF`, per-frame max median 0.6714 — not a
restatement at the 0.90 line.

Ledger row recorded: `python docs/gate_e_ledger.py record
/home/tolga/.issue-solver/runs/20261126-213551-179/gatee/is179-rd_std_ratio_20_60-f81ac76a
--measured 2026-11-26` → `docs/gate_e_ledger.csv`.

Module sha1 (LF-normalised, measured `python docs/measure_rd_std_ratio_20_60.py`):
`58a8592edac58ff55328bea56d8db4ef5aa15dd8`.

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole suite):

```
python -m pytest -q tests/test_rd_std_ratio_20_60.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

**1,710 passed, 7 skipped, 1 failed.** The one failure is
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` — expected, per the
issue-solver's own rules, until the launcher's Gate E run and a later receipt session record
this port's ledger row. `tests/test_rd_std_ratio_20_60.py` alone: 20 passed.

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in for a GitHub runner
without AVX-512 — the four features issue-solver's rules name, not this machine's full
dispatchable set, which also has `AVX512CD`/`AVX512_CLX`/`AVX512_CNL`/`AVX512_ICL` enabled):
`python docs/measure_rd_std_ratio_20_60_cpu.py` — **20 passed** (just
`tests/test_rd_std_ratio_20_60.py`; the ledger/readme/wiring modules above are not
CPU-sensitive and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 413 → 414 (`tests/test_altport2_ports.py`); `CATEGORY_BUCKETS["volatility"]`
  42 → 43.
- README: 413 → 414 registered, 421 → 422 callable, volatility (42) → (43).
- `docs/MLCompanionContract.md`: 758 → 759 tagged and 384 → 385 `SF` (newest first in the
  chain). `RD_STD_RATIO_20_60_20_60` tags `SF` because a rolling stdev and its own rolling
  average both scale exactly with an exactly-representable price rescale, cancelling
  bit-identically in the ratio.
- `docs/IndicatorDictionary.md`, regenerated with this environment's package (`python
  docs/gen_indicator_dictionary.py`): adds `rd_std_ratio_20_60` under `## volatility (43)`, and
  the `SF` tag list.
- `Category`: `rd_std_ratio_20_60` is placed alphabetically between `rd_range_contraction` and
  `rogers_satchell` in `volatility`.
