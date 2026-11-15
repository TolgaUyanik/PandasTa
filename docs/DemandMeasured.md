# demand — measured (issue #33)

> **Status: Gates A-F cleared.** Gate E ran on 2026-11-02 (launcher run
> `is33-demand-006099d0`), verdict **SHIP**, recorded in `docs/gate_e_ledger.csv`. Issue #33
> closes by ship.

Sibbet's Demand Index / Aspray's Demand Oscillator, Kaufman (2013) ch. 12's reading, as
asked for by issue #33. Module `pandas_ta/volume/demand.py`, column `DEMAND_10_10` (tagged
`SF` by `docs/IndicatorDictionary.md`). Tests: `tests/test_demand.py` (16, all passing).
Numbers below: `python docs/measure_demand.py`. Environment: this worktree's pinned
pandas/numpy (pandas 2.3.3). Measured 2026-11-02.

## Gate A: the primary source is NOT available in this worktree — read this before trusting the column

The issue's own text calls the formula "a reading of garbled PDF text... as far as the PDF
text can be read" and says "Gate A must start from the book page or Aspray's article." Per
this session's rules, `docs/pine/` and web access are unavailable, and the owner's
`docs/issues/032-DEMAND-INDEX.md` copy (read first, before any code) contains the same text
quoted in the GitHub issue — no page image, no scan, no copy of the TASC articles. **This
session could not verify the formula against the primary source**, and a future session
with access to the book page or Aspray's article should treat this module as unverified
until re-checked.

Given that constraint, the issue's formula is implemented as given, with three reading
decisions the formula itself leaves open (also documented in the module docstring's "WHAT
IS ASSUMED" section) — all three are ASSUMPTIONs, not measured against an alternative
reading:

1. **"max 2-day high-low range"** → `rolling(2).max()` of the daily `high - low` range (the
   larger of today's and yesterday's range), not a 2-bar high minus a 2-bar low.
2. **"ΔC/C"** → the plain 1-bar percent change, `close.pct_change()`.
3. **Unchanged close (ΔC == 0, not addressed by the source at all)** → treated as neutral:
   `BP = SP = volume`, so the oscillator reads exactly 0. This decision does double duty as
   the ΔC-near-zero guard the issue explicitly calls for ("Division by ΔC near 0 needs a
   guard, and BIST tick rounding makes ΔC = 0 common") — on the synthetic tick-rounded walk
   used for Gate C below, exact ΔC = 0 occurs on 21 of 1,200 bars (1.75%), so the guard is
   exercised on realistic data, not just a hypothetical.

**Scale-free decision (the issue's own "decide at Gate A" point).** The issue flags that the
raw oscillator (BP − SP) is in volume units and offers two options: divide by volume, or by
`SMA(V, n)`. This ships the second — `raw / SMA(volume, vol_length)` — because `raw` is
linear in `volume` on every branch (rising: `V - V/denom = V*(1-1/denom)`; falling:
`V/|denom| - V = V*(1/|denom|-1)`; flat: `0`), so the ratio to a trailing volume average
cancels a uniform volume rescale exactly, which the per-bar division alone would not protect
against on a single unusually large/small print. Measured, not assumed — see Gate D.

## Round 1 review fix: the flat-bar guard had a warm-up gap

A `/brutally-honest-review` CRITICAL finding caught a real bug before it shipped: the
unchanged-close guard (decision 3 above) masked the output on `pct_chg.notna()` only, not on
whether `k` (the volatility scale) had itself finished warming up. `k` needs `range_sma`
valid, which warms up **one bar later** than a plain `rolling(length)` because of the
leading `rolling(2).max()`, while `avg_vol` (the volume normaliser) warms up at
`rolling(vol_length)`'s own rate. Whenever `vol_length <= length`, there is a real window
where `avg_vol` is defined but `k` is not — a flat bar landing inside that window used to
read a fabricated `0.0` instead of `NaN`. Fixed by masking on `pct_chg.notna() & k.notna()`
(`pandas_ta/volume/demand.py`). Two regression tests pin it:
`test_flat_bar_inside_the_k_warmup_gap_is_nan_not_zero` (default `length=vol_length=10`, the
1-row gap at index 9) and `test_flat_bar_inside_an_asymmetric_k_warmup_gap_is_nan_not_zero`
(`length=50, vol_length=5`, a 46-row gap, probed at index 20). Re-measuring after the fix:
every number in the Gates table below is unchanged (no flat bar in the seed-17 walk happened
to land inside the 1-row default gap), confirming the bug was real but not exercised by the
original measurement run — the fix and its regression tests, not luck, are what rules it out
now.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | **primary source unavailable — see above.** Self-consistent against the issue's own formula | Hand-derived 3-bar example (length=1, vol_length=1, every rolling window a no-op except the 2-bar range max): rising bar reads exactly 31/33 = 0.939394, falling bar reads exactly -277/297 = -0.932660, derived by hand from the formula, not by re-running the module. Matches an independent per-bar loop (written from the formula) at 4 spot-checked bars (30, 120, 250, 399) on a 400-bar synthetic walk, rel. tolerance 1e-9 |
| B Causality | pass | Future-perturbation sweep, 31 offsets: real module **0 of 31** leaks. One look-ahead mutant (`pct_chg = close.pct_change()` → `.shift(-1)`, `importlib` source read, `exec`'d in memory) is shown live (differs from the real module), then caught at **31 of 31** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,200-bar tick-rounded walk (seed 17, σ=1.5%, tick=0.05, length=10, vol_length=10): **1,190 of 1,200** bars non-NaN (99.17%) — the 10 NaN bars are exactly the combined K/volume-SMA warm-up (`max(length, vol_length)`), not a wider gap. 1,170 distinct values among the 1,190. Range [-44.08, 26.64], median exactly 0.0, median\|value\| 0.4630. The unchanged-close guard (decision 3 above) fires on 21 of 1,200 bars |
| D Scale-free | pass | Price axis (high/low/close together) and volume axis measured **independently**. x8/x64: **bit-identical, 0.0 max\|diff\|** on both axes. x10/x3.7: price max\|diff\| 1.24e-11 / 1.79e-11, volume max\|diff\| 7.11e-15 / 1.42e-14 — both axes, both scales, well under the 1e-9 tolerance the test asserts, with matching NaN masks. `0 < 1,190 fires < 1,200` and 1,170 distinct values rule out a constant column |
| E Attribution | **SHIP** — run `is33-demand-006099d0`, 2026-11-02, 89 ALTPORT-1 frames, 687 comparators (329 compute_all + 358 manifest), pooled n 397,742 | `DEMAND_10_10`: max\|ρ\| **0.4807** vs `Pivot_Band_State` (manifest), per-frame max median\|ρ\| **0.4585** (same comparator), 0/89 frames ≥ 0.90. Well under the 0.76 SHIP line. Recorded in `docs/gate_e_ledger.csv` |
| F Suites | this repo only; parent repo (`Backtesting`) and Gate E are run by the launcher in clean worktrees | `python -m pytest -q` (this session, pre-ledger-record): **3 failed, 4,063 passed, 83 skipped** — the two pre-existing known breaks plus `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (resolved by this receipt session's ledger record, below) |

## Wiring

`Category` **267 → 268** (`volume` **28 → 29**); `df.ta.<name>()` accessor count **275 →
276**. Touch points: `pandas_ta/volume/demand.py` (module), `pandas_ta/volume/__init__.py`
(export), `pandas_ta/__init__.py` → `Category["volume"]` (discovery), `pandas_ta/core.py` →
`AnalysisIndicators.demand` (accessor), `tests/test_demand.py` (tests). `README.md`'s
headline and `volume (29)` row, and `docs/IndicatorDictionary.md` (regenerated), both
updated and checked by `tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s
running tag count updated **613 → 614** tagged columns, **258 → 259** `SF`, checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL`/`CATEGORY_BUCKETS` constants updated to
match.

## Receipt (2026-11-02)

Gate E ran SHIP, so `demand` ships as-is. `docs/gate_e_ledger.csv` carries the row
(`demand:DEMAND_10_10 SHIP 0.4807 vs Pivot_Band_State`). Issue #33 is closed by ship, not by
revert.
