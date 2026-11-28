# Dip below the 10-day high, in average-range units (10, 25) — measured (`rd_dip_depth_10_25`)

Issue #181 (RD-DIP-DEPTH-10-25), from the 2026-10-25 ResearchIntel Reddit-KB scan, round 6
(`docs/issues/screen/candidates_r6.csv`). Crowd talk (Reddit, tier 4): the definition comes
from a post or comment, and nothing in this port tests what the poster says it does —
existence, not evidence.

**Source:** Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:1rjvxjy (2026-03-03)
https://www.reddit.com/r/algotrading/comments/1rjvxjy/; rd:Daytrading:1rktyiu (2026-03-04)
https://www.reddit.com/r/Daytrading/comments/1rktyiu/; rd:algotrading:1cwsco8 (2024-05-20)
https://www.reddit.com/r/algotrading/comments/1cwsco8/; rd:Trading:1rktege (2026-03-04)
https://www.reddit.com/r/Trading/comments/1rktege/ — the poster's words: "close < (10 days
high - 2.5 * (25 days average high - 25 days average low)". Claimed use: oversold
mean-reversion entry on SPY, entering when the ratio below is > 2.5 together with IBS < 0.3
— **not independently tested here.** A Reddit post is not a script, so there is no source
line number to cite; Gate A below reads the formula directly from the issue's own
restatement (its own instruction: "Gate A starts from the source formula, not the
prototype"), not from the screen prototype (`docs/issues/screen/ind_screen_r6.py`'s
`rd_dip_depth_10_25`, which reads the same way): `(HHV(high, 10) - close) / (SMA(high, 25) -
SMA(low, 25))`. Rearranging the poster's own inequality onto one side gives exactly this
ratio `> 2.5` — the ratio IS the poster's own quantity; the `> 2.5` threshold is an entry
rule on top of it, not shipped here (the same convention `rd_std_ratio_20_60` and
`rd_range_contraction` use for their own posters' thresholds).

**Status:** Gates A-E measured below. Whole-suite run is owed to the launcher, per the
issue-solver's own rules (it must not run the whole suite).

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/momentum/rd_dip_depth_10_25.py` | momentum | `RD_DIP_DEPTH_10_25_10_25` | continuous, >= 0 on valid OHLC (trailing high minus close is non-negative); measured 0.000155..27.656715 on a 1,200-bar synthetic frame below; NaN during warm-up or where the average range is exactly zero |

Tests: `tests/test_rd_dip_depth_10_25.py` (20 tests). Numbers: `python
docs/measure_rd_dip_depth_10_25.py`, run from the repo root. Environment: Python 3.11.2,
pandas 2.3.3, numpy 1.26.4. Measured 2026-11-27.

## Decisions

1. **`length`/`avg_length` are parameters, not hard-coded** — same convention as every other
   `rd_*` port in this fork (e.g. `rd_std_ratio_20_60`'s `length`/`avg_length`): the issue's
   own numbers (10, 25) are kept as the module's own defaults, but the shape generalises.
2. **`HHV` is a plain trailing rolling max** (`high.rolling(length).max()`) and **`SMA` is a
   plain trailing rolling mean** (`.rolling(avg_length).mean()`) — matching both the screen
   prototype's own helpers (`tsmax(x, n)` = `x.rolling(n).max()`, `mean(x, n)` =
   `x.rolling(n).mean()`) and the issue's own wording.
3. **The two rolling windows are independent, not nested** — `HHV(high, length)` and
   `SMA(high, avg_length) - SMA(low, avg_length)` each read raw `high`/`low` directly and
   combine only in the final ratio, unlike `rd_range_contraction`'s nested spread-then-MA.
   The combined warm-up is therefore `max(length, avg_length) - 1` bars, not
   `length + avg_length - 2`.
4. **A zero average range reads NaN, not ±inf** — a dead-flat market with an identical
   25-bar average high and average low makes the divisor exactly 0; `np.inf`/`-np.inf` are
   replaced with NaN explicitly, the same guard `rd_range_contraction` and
   `rd_std_ratio_20_60` use for their own zero-denominator case.
5. **Column name carries both parameters**, `RD_DIP_DEPTH_10_25_{length}_{avg_length}` — e.g.
   `RD_DIP_DEPTH_10_25_10_25` at defaults, `RD_DIP_DEPTH_10_25_5_15` at `length=5,
   avg_length=15`. The fixed `10_25` in the module/function name itself is the candidate's
   own name from the issue, kept as a literal suffix even though the parameters are not
   hard-coded (same convention as `rd_std_ratio_20_60`, `rd_vwio_10`).
6. **Category: momentum.** The ratio is a mean-reversion depth oscillator (the poster's own
   claimed use is an oversold entry), and the issue's own prototype measurement puts its
   nearest comparators in momentum (`kdj_J_9_3`, `willr`), not in a volatility- or
   trend-regime column.

## Gate A — the formula, read bar-by-bar

The issue's own formula (not the prototype — the issue's explicit instruction), read
literally in the module's docstring:

```
numerator = HHV(high, length) - close
denominator = SMA(high, avg_length) - SMA(low, avg_length)
RD_DIP_DEPTH_10_25 = numerator / denominator
```
with `length=10, avg_length=25`; `HHV` a trailing rolling max, `SMA` a simple rolling mean;
division by zero → NaN.

A hand-derived fixture, chosen on paper before the module ran
(`tests/test_rd_dip_depth_10_25.py::test_hand_derived_value`): a flat `high=10.0` for 3 bars
then a step to `high=20.0` for 5 more, constant `low=8.0` and constant `close=9.0`, at
`length=2, avg_length=4`. `HHV(high,2) = [nan,10,10,20,20,20,20,20]`; at bar 3 (0-indexed),
numerator `= 20 - 9 = 11`, `mean(high,4) = mean(10,10,10,20) = 12.5`, denominator
`= 12.5 - 8 = 4.5`, ratio `= 11 / 4.5 = 2.444444` exactly on paper; at bar 6, numerator `=
11`, `mean(high,4) = mean(20,20,20,20) = 20`, denominator `= 12`, ratio `= 11 / 12 =
0.916667`. The module's measured output
(`python docs/measure_rd_dip_depth_10_25.py`): **`bar3 = 2.444444`, `bar6 = 0.916667`** —
both match.

Cross-checked against an independent per-window Python loop built straight from the formula
above (`numpy.lib.stride_tricks.sliding_window_view` + `np.max`/`.mean()`, not pandas
`.rolling`, and not read from the module) on a 400-bar synthetic OHLC walk (seed 7,
length=10, avg_length=25, 376 defined bars): NaN masks identical, **max |diff| 9.681e-13**
(`test_matches_an_independent_loop`, `python docs/measure_rd_dip_depth_10_25.py`) — float
noise from the two different reduction orders (pandas `.rolling().max()`/`.mean()` vs. a
Python-level max/mean over a numpy slice), not a logic mismatch; the test
(`tests/test_rd_dip_depth_10_25.py:88`) bounds this comparison at `rtol=1e-12, atol=1e-12`,
a margin the measured 9.681e-13 sits inside once `rtol*|ref|` (values up to ~27) is counted,
not the 1e-9 tolerance used for the x10/x3.7 scale test below.

## Gate B — causality

- **The real module never reads the future, swept, not spot-checked.** Two 1,200-bar
  synthetic OHLC walks (seeds 1 and 2) spliced at `J`: bars `< J` come only from seed 1 in
  both the base and the spliced series, so if the module reads no later bar than `T` its
  output on `[0, J)` cannot move. Measured over **25 swept J values** (`J` = 100, 140, ...,
  1060, past the 24-bar default warm-up; `python docs/measure_rd_dip_depth_10_25.py`): **real
  module leaked at 0 of 25**.
- **The mutant (the final ratio assignment with a `.shift(-1)` appended, reading one bar into
  the future) is live** (differs from the real module on the unperturbed frame) **and leaked
  at 25 of the same 25 swept J values** — every offset, since a one-bar shift of a
  continuous, almost-everywhere-changing ratio moves essentially every downstream bar
  (`tests/test_rd_dip_depth_10_25.py::test_lookahead_mutant_is_caught`).

## Gate C — reachability

Synthetic, from the port session:

- **1,200-bar frame (seed 4):** 1,176 of 1,200 bars fire (24-bar warm-up); values range
  **0.000155 to 27.656715** across **1,176 distinct values** — all non-negative (the trailing
  high is at least the current close on valid OHLC).
- **10 independent 600-bar frames (seeds 100-109):** every frame fires on 576 of 600 bars
  (the fixed 24-bar warm-up) and reads 576 distinct values — consistent with the single-frame
  figures above, not an outlier.
- **A zero average range reads NaN by construction**
  (`test_zero_average_range_reads_nan_not_inf`); not observed on the random synthetic frames
  above (a GBM-style walk's high/low range is never exactly constant for 25 bars), which is
  expected, not a defect.
- **Real-data reachability**, measured on the launcher's Gate E run
  (`is181-rd_dip_depth_10_25-4dcb8d6b`): 396,713 non-NaN bars of 398,849 pooled across the 89
  ALTPORT-1 frames, 389,521 of them non-zero; no `degenerate.csv` row for this column (the
  run's one `degenerate.csv` row is the comparator `squeeze_SQZ_NO`, constant) -- the same
  shape `flat_spots`' entry uses in `docs/MLCompanionContract.md`.

## Gate D — scale-free

- **Bit-identical under a power-of-two price rescale (x8/x64), tolerance under any other
  (x10/x3.7).** For an exactly-representable rescale by `k`: `HHV(high*k, length)` picks the
  existing element that was the maximum before scaling, exactly `k` times that element
  (scaling every element of a window by the same exact `k` scales its max by that same
  factor), and `close*k` scales exactly by `k` too, so `numerator' = k*HHV(high,length) -
  k*close = k*numerator` exactly (IEEE-754 subtraction of two exactly-k-scaled operands, for a
  power-of-two `k`, is itself exact). `SMA(high*k, avg_length)` and `SMA(low*k, avg_length)`
  are each a sum of `k`-scaled terms divided by the same integer `avg_length`, which returns
  exactly `k` times the unscaled average, so `denominator' = k*denominator` exactly too. The
  final ratio `(k*numerator)/(k*denominator)` is then IEEE-754 division of two operands both
  scaled by the identical exact `k`, which returns a bit-identical quotient to the unscaled
  division — the same cancellation `rd_range_contraction`
  (`pandas_ta/volatility/rd_range_contraction.py`) relies on for its own ratio of range-based
  terms. A non-power-of-two rescale (x10, x3.7) is not exact at the max or division steps, so
  that stays a tiny-tolerance claim.
- **Measured on the 1,200-bar seed-4 frame, 1,176 co-finite cells**
  (`python docs/measure_rd_dip_depth_10_25.py`):

  | k | exact mismatches | max abs diff | max rel diff |
  |---|---|---|---|
  | 8.0 | 0 | 0.0 | 0.0 |
  | 64.0 | 0 | 0.0 | 0.0 |
  | 10.0 | 1161 of 1176 | 2.089e-12 | 1.356e-10 |
  | 3.7 | 1175 of 1176 | 2.519e-12 | 1.526e-10 |

  x8/x64 are exact zero (`test_price_scale_is_bit_identical`, `==` comparison, not a
  tolerance). x10/x3.7 land near the float noise floor.
  `tests/test_rd_dip_depth_10_25.py::test_scale_stays_within_a_tiny_tolerance` bounds the
  x10/x3.7 case at `rtol=1e-9, atol=1e-9` — a generous margin above the measured figures, not
  the measured figures themselves, per the issue-solver's own CPU-variant rule (the exact last
  bit is the CPU's dispatched kernels' call, not this module's logic).
- `0 < fires < n`, not constant: 1,176 of 1,200 bars fire on the 1,200-bar frame above, 1,176
  distinct values, min 0.000155 and max 27.656715 (never negative on valid OHLC).

## Gate E — attribution

**Measured on the shipped module**, launcher run `is181-rd_dip_depth_10_25-4dcb8d6b`
(`gate_e_overlap.py run --module pandas_ta.momentum.rd_dip_depth_10_25`), 89 ALTPORT-1 BIST
frames, 398,849 pooled bars, 687 comparators (329 `compute_all` + 358 `ml_features` manifest),
canary bit-equal on AKBNK.IS/BIENY.IS/AGHOL.IS/SASA.IS:

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---|---|---|---|---|
| `RD_DIP_DEPTH_10_25_10_25` | 0.8401 | `kdj_J_9_3` | 396,713 | 0.8497 (against `Dist_to_Tenkan_pct`) | **DISCLOSE_GAP** |

Pooled max |ρ| 0.8401 and per-frame max median 0.8497 both sit under the 0.90 STRUCK line
(`r3-perframe-0.90` band), so this is DISCLOSE_GAP, not STRUCK — ships as-is, disclosed. The
measured number matches the issue's own prototype measurement almost exactly (0.8401 vs
`kdj_J_9_3`, same comparator, same band), confirming the prototype's number carried through
the port unchanged. Ledger row recorded: `python docs/gate_e_ledger.py record
{runs}/20261127-070101-181/gatee/is181-rd_dip_depth_10_25-4dcb8d6b
--measured 2026-11-27`.

**Non-redundancy against `willr`.** `willr`'s own formula,
`100*(close-HHV(high,n))/(HHV(high,n)-LLV(low,n))`, shares this port's `HHV(high,n) - close`
numerator shape — the structurally closest of the two named comparators, closer than either
comparator `rd_std_ratio_20_60` disclosed against. The two are not the same feature: `willr`
normalises that gap by the SAME n-bar window's own high-low range, while this port
normalises it by a SEPARATELY-averaged 25-bar mean-high-minus-mean-low — a longer, smoother
denominator that does not collapse to `willr`'s own range at any parameter choice. That
difference is why the measured 0.8401/0.8241 sits in DISCLOSE_GAP rather than STRUCK: a
close denominator, not an identical one.

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole suite):

```
python -m pytest -q tests/test_rd_dip_depth_10_25.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

**1,726 passed, 7 skipped, 1 failed**, measured 2026-11-27 before the ledger row existed. The
one failure was `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` —
expected at that point, per the issue-solver's own rules. The row now exists in
`docs/gate_e_ledger.csv` (run `is181-rd_dip_depth_10_25-4dcb8d6b`), so that test no longer
fails on this port. `tests/test_rd_dip_depth_10_25.py` alone: 20 passed.

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in for a GitHub runner
without AVX-512 — the four features issue-solver's rules name, not this machine's full
dispatchable set, which also has `AVX512CD`/`AVX512_CLX`/`AVX512_CNL`/`AVX512_ICL` enabled):
`python docs/measure_rd_dip_depth_10_25_cpu.py` — **20 passed** (just
`tests/test_rd_dip_depth_10_25.py`; the ledger/readme/wiring modules above are not
CPU-sensitive and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 415 → 416 (`tests/test_altport2_ports.py`); `CATEGORY_BUCKETS` unchanged
  (momentum is not one of the three tracked buckets in that file).
- README: 415 → 416 registered, 423 → 424 callable, momentum (90) → (91).
- `docs/MLCompanionContract.md`: 760 → 761 tagged and 386 → 387 `SF` (newest first in the
  chain). `RD_DIP_DEPTH_10_25_10_25` tags `SF` because `HHV(high,length)-close` and
  `SMA(high,avg_length)-SMA(low,avg_length)` both scale exactly with an exactly-representable
  price rescale, cancelling bit-identically in the ratio.
- `docs/IndicatorDictionary.md`, regenerated with this environment's package (`python
  docs/gen_indicator_dictionary.py`): adds `rd_dip_depth_10_25` under `## momentum (91)`, and
  the `SF` tag list.
- `Category`: `rd_dip_depth_10_25` is placed alphabetically between `qqe` and `roc` in
  `momentum`.

## Next step

None. Gates A-F measured; DISCLOSE_GAP, ships as-is. Whole-suite runs are the launcher's.
