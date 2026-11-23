# Normalised Buy/Sell Pressure, net — measured (`fn_baspn_net`)

PandasTa issue #150. Source: finta (LGPL-3.0, archived) — existence, not evidence per
CLAUDE.md. finta's own source is NOT in this worktree; the formula is recalled from the
issue text, never read off finta's code:

    BASPN = EMA20((C-L)/EMA40(C-L) * V/EMA40(V)) - EMA20((H-C)/EMA40(H-C) * V/EMA40(V))

**Status: Gates A–D cleared. Gate E: pending, run by issue-solver after this session.**
`fn_baspn_net` is in `Category["volume"]`, as `pfe` and `kalman_trend` shipped under the
same deferral before their own Gate E rows were recorded (`docs/PfeMeasured.md`,
`docs/KalmanTrendMeasured.md`) — registering it before Gate E follows that precedent.

Shipped: `pandas_ta/volume/fn_baspn_net.py`, one column `FN_BASPN_NET_{slow}_{fast}`
(default `FN_BASPN_NET_40_20`). Tests: `tests/test_fn_baspn_net.py` (25). Numbers:
`python docs/measure_fn_baspn_net.py` and `python docs/measure_fn_baspn_net_cpu.py`.
Environment: Python 3.11.2, pandas 2.3.3, numpy 1.26.4. Measured 2026-11-23.

## The one Gate-A decision the source formula does not spell out

The formula names "EMA" without fixing an implementation (SMA-seeded warm-up vs. a bare
`Series.ewm()`, `adjust=True` vs `adjust=False`). This port uses this fork's own `ema()`
building block (`pandas_ta/overlap/ema.py`: SMA-seeded warm-up, `adjust=False` recursion)
for every EMA in the formula, exactly as every other EMA-based indicator already shipped
in this fork does (`kvo`, `macd`'s signal line, …), rather than introducing a second,
bespoke EMA implementation just for this port. This is a design choice, not a correctness
gap: the published definition does not specify a seeding method, so matching this fork's
existing convention is the more defensible reading than inventing a new one.

A consequence worth recording: the OUTER 20-bar EMA's own SMA-seed window (`slow`-1 = 39 ≥
`fast` = 20 bars of the fast window) falls entirely inside the inner EMAs' NaN warm-up, so
the SMA seed itself evaluates to NaN and is a no-op — the outer EMA reduces to a plain
recursive EMA seeded on its first valid input (bar 39, 0-indexed). This was traced, not
assumed: `docs/measure_fn_baspn_net.py` reports "first finite bar (0-indexed): 39", matching
the generated `docs/IndicatorDictionary.md` warm-up column for `fn_baspn_net` (39).

## The source formula is already scale-free, in the strong sense

Every term in BASPN divides a quantity by an EMA of ITSELF: `(C-L)` by `EMA40(C-L)`, `(H-C)`
by `EMA40(H-C)`, `V` by `EMA40(V)`. A constant rescale of price (high, low, close together)
or of volume cancels exactly inside each ratio, so the column is not merely proportionally
rescaled under a price or volume rescale — it is UNCHANGED. No log-return or percent
conversion was needed, unlike most of this fork's ports (`pfe`, `tf_median_absdiff_20`, …).

## Division-by-zero guard

Each ratio's denominator is guarded with `.replace(0, NaN)` before dividing (matching this
fork's `non_zero_range` convention used elsewhere, e.g. `cmf`). An EMA of a non-negative
series (`close - low >= 0`, `high - close >= 0`, `volume > 0`) is exactly zero only if every
value feeding it over its full decay has been zero — a degenerate case not exercised on the
realistic walks measured below, where every fired bar is non-zero (see Gate C).

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass | An independent scalar-loop re-implementation of this fork's own EMA algorithm (SMA-seeded warm-up, then a recursive EMA that skips a leading NaN block and seeds on the first valid value — written from `ema.py`'s documented algorithm, never by importing it), composed by hand into the BASPN formula, agrees with the shipped column on 1,161 of 1,161 compared bars of a 1,200-bar synthetic OHLCV walk, max\|diff\| 0.0 (exact). NaN masks match. A second, independent hand-worked check (`test_hand_derived_literal_at_the_warmup_boundary`) pins a literal fraction, 4/9, at `slow=2, fast=1` on a 3-bar frame — `fast=1` makes the outer EMA an exact pass-through (`alpha = 2/(1+1) = 1`), so the arithmetic is worked by hand on paper, not by re-running `_reference`. |
| B Causality | pass | 32-offset future-perturbation sweep (`range(60, 1150, 35)`, past the 39-bar warm-up): real module leaks at 0 of 32. Two mutants (`importlib`-read source, `exec`'d in memory): the close read into the buy/sell pressure legs taken one bar forward (`close.shift(-1)`), and the volume read into the normalising ratio taken one bar forward (`volume.shift(-1)`). Both are live (differ from the real module) and both are caught at 32 of 32 offsets on the one base/perturbation frame pair tested. |
| C Reachability | synthetic only | 1,200-bar OHLCV walk (seed 11, σ=0.02): 1,161 of 1,200 finite (39-bar warm-up), 1,161 non-zero (0 exact zeros), 1,161 distinct values, 579 positive / 582 negative, range [-0.6759, 0.8872], mean 0.0133. Real-data counts owed to Gate E. |
| D Scale-free | pass | ×8 / ×64 bit-identical on all 1,161 fired bars with matching NaN masks, for a price-only rescale (high/low/close × k, volume unchanged), a volume-only rescale (volume × k, price unchanged), AND a combined rescale with DIFFERENT factors on each side at once (price × k, volume × k/2, both still powers of two) — `test_a_power_of_two_combined_price_and_volume_scale_is_bit_identical`, confirming the two cancellations are independent, not coupled by an unseen shared term. ×10 max\|diff\| 2.554e-14, ×3.7 max\|diff\| 2.620e-14 (price-only); volume-only max\|diff\| 8.88e-16 at both ×10 and ×3.7. `0 < 1,161 < 1,200` fires, 1,161 distinct values (non-constant). Re-run clean with `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` (`docs/measure_fn_baspn_net_cpu.py`): same 25/25 tests pass — no exact bit-count or tolerance tighter than what is stated above is pinned, so the CPU-variant kernels on a GitHub runner cannot break this suite. |
| E Attribution | **pending** | Run by issue-solver after this session: `gate_e_overlap.py run --module pandas_ta.volume.fn_baspn_net --name fn_baspn_net`. The owner's pre-screen prototype (`docs/issues/screen/ind_screen_r5.py`, candidate `fn_baspn_net`, a scale-free "Buy - Sell" form, NOT this exact shipped EMA implementation) measured max \|ρ\| 0.7750 vs `adosc_norm_Pctl` (n=392,787), per-frame max median 0.7879 → DISCLOSE on the prototype. That is NOT this port's Gate E: the prototype used a different EMA implementation (`Series.ewm(adjust=True)` directly, no SMA seed) and is cited here only as context for what range to expect, not as this port's measurement. |
| F Suites | this repo only (the launcher runs both whole suites) | `python -m pytest -q tests/test_fn_baspn_net.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`: 1,451 passed, 7 skipped, 1 expected failure (`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` — Gate E owed, per CLAUDE.md's "owed, not failed" rule; resolved once the ledger row is recorded). Whole suites: run by issue-solver in clean worktrees (see the PR body). |

## Wiring counts, read back

`Category` total 381 (was 380), `Category["volume"]` 44 (was 43). README headline and the
`volume (44)` row updated; `docs/IndicatorDictionary.md` regenerated (`383` indicators
probed, 1 new SF-tagged row, warm-up 39); `docs/MLCompanionContract.md`'s running SF tally
updated 359 → 360 (726 tagged columns total, was 725); `CATEGORY_TOTAL` 381 and
`CATEGORY_BUCKETS["volume"]` 44 in `tests/test_altport2_ports.py`.

## Final suite run

`python -m pytest -q tests/test_fn_baspn_net.py tests/test_readme_counts.py
tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
tests/test_prose_counts_match_the_csvs.py`: 1,451 passed, 7 skipped, 1 expected failure
(Gate E owed). Both repos' whole suites: run by issue-solver in clean worktrees (see the PR
body).

## To close

1. Run `gate_e_overlap.py run --module pandas_ta.volume.fn_baspn_net --name fn_baspn_net`
   in the parent repo, then `docs/gate_e_ledger.py record <run dir> --measured <date>`.
2. Apply CLAUDE.md's bands to the measured max \|ρ\|. SHIP < 0.76 ships as-is; DISCLOSE_GAP /
   DISCLOSE ship with the number recorded above; STRUCK (pooled ≥ 0.90 or a top-5
   comparator's per-frame median ≥ 0.90) reverts the module, the export, the `Category`
   entry, the accessor, the tests, the README counts, the dictionary row and the
   `MLCompanionContract` count, keeping this file as the receipt.
3. Fill Gate C from the real BIST frames used by that run.
4. Run both suites.
