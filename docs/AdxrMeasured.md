# ADXR, Average Directional Movement Index Rating — measured (`adxr`)

QuantConnect Lean (Apache-2.0) `AverageDirectionalMovementIndexRating.cs`:

    adxr = (ADX + ADX[period]) / 2

Also jesse (MIT) `adxr.py`, the same average. Candidate `lean_adxr_14` from the
2026-10-24 library catalog screen round 2 (`docs/issues/screen/ind_screen_r2.py`,
`docs/issues/screen/candidates_r2.csv`). Issue #110 / LEAN-ADXR-14.

**Status: Gates A, B, D cleared; Gate C synthetic only (real-data counts owed);
Gate E pending, run by issue-solver after this session; Gate F this repo green
(3 pre-existing failures, none naming `adxr`, see below).**

Shipped: `pandas_ta/trend/adxr.py`, one column `ADXR_<length>` (default
`ADXR_14`), range [0, 100] (inherits ADX's own range). Tests: `tests/test_adxr.py`
(13). Numbers: `python docs/measure_adxr_proxy.py`. Environment: pandas 2.3.3,
numpy 1.26.4 (per `.github/workflows/ci.yml` pins), Python 3.11. Measured
2026-10-30.

## Design choice: built on this fork's own `adx()`, not re-derived

The round-2 prototype (`ind_screen_r2.py:86-90`) computes ADX from scratch with
its own `dm_wilder`/`dx_wilder` helpers, then applies the Lean averaging step.
This port does not repeat that derivation: it calls this fork's own, already-
shipped `pandas_ta.trend.adx.adx()` (Wilder RMA smoothing, scalar 100) for the
`ADX_<length>` column, then averages it against its value `length` bars back —
the two-line Lean formula, applied directly to the source formula rather than
transliterating the prototype's independent ADX loop. `adx()`'s own
correctness is upstream and out of scope for this port; Gate A below is
specifically about the averaging step, checked by recomposing it independently
of `adxr.py` in the test (calling `adx()` directly and doing the shift-and-
average arithmetic in the test body, not in the module under test).

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass | `test_matches_the_lean_formula_recomposed_from_adx` (length 14 and 7): `adxr()` output bit-identical to `(adx()["ADX_<n>"] + adx()["ADX_<n>"].shift(n)) / 2` computed independently in the test, on a 900-bar synthetic OHLC walk. `test_bounded_zero_to_hundred`: output in [0, 100] (an average of two ADX reads, each already in that range). |
| B Causality | pass | Future-perturbation sweep, 15 offsets (60..830 step 55) on a 900-bar OHLC walk: real module leaks at 0/15. A look-ahead mutant (`importlib` source read, the backward `adx_.shift(length)` flipped to a forward `adx_.shift(-length)`, `exec`'d into a fresh in-memory module) is proved live (differs from the real module's output) and caught at 15/15 offsets. |
| C Reachability | synthetic only | 900-bar synthetic trending walk (seed 11, σ=0.02): 859 of 900 bars finite (41-bar warm-up: `adx()`'s own RMA warm-up plus the `length`-bar backward shift), 859 distinct values, range [8.693323, 28.490809]. **Real-data counts owed**, pending Gate E. |
| D Scale-free | pass | ×8 / ×64 OHLC scaling: bit-identical, max \|diff\| 0.0 (ADXR is an average of two ADX reads, and ADX is itself built from ratios — `scalar / atr_`, `(dmp - dmn).abs() / (dmp + dmn)` — that cancel a price scale exactly). ×10: max \|diff\| 7.105427e-14, well inside the 1e-9 tolerance pinned by `test_other_scales_within_tolerance`. `0 < 859 < 900` fires, plus 859 distinct values (`test_fires_on_real_shaped_data_and_is_not_constant`), so a constant column cannot pass. `test_too_short_a_series_returns_none` pins the other edge: a 10-bar series (below `2 * length`) returns `None` rather than an all-NaN series. |
| E Attribution | **PENDING** — run by issue-solver after this session via `gate_e_overlap.py run --module pandas_ta.trend.adxr --name adxr`. The *prototype* `lean_adxr_14` (a different implementation — its own `dx_wilder`, not this fork's `adx()`) measured max \|ρ\| 0.8806 vs `ADX` (compute_all, n=396,446), top-5 per-frame max median 0.8796 → `DISCLOSE_GAP` band on the `r3-perframe-0.90` scale. ADXR is `(ADX + ADX[14]) / 2` by construction, so a high correlation with `ADX` is expected on both implementations; the prototype's number is context from the issue, not a measurement of the shipped module, and is not a substitute for the real Gate E run. |
| F Suites | this repo only | `python -m pytest -q`: 3 failed, 3271 passed, 83 skipped (2026-10-30). None of the 3 failures name `adxr`: `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows` (needs the sibling `../AlternativeRepos` checkout, deselected in CI), `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (expected until the ledger row is recorded after Gate E runs), `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` (CLAUDE.md's documented pre-existing break from `8d8f705`, present on a clean checkout before this port). Parent repo suite run by the launcher. |

## Wiring (five touch points)

1. `pandas_ta/trend/adxr.py` — the indicator.
2. `pandas_ta/trend/__init__.py` — package export.
3. `pandas_ta/__init__.py` → `Category["trend"]` — discovery / `df.ta.strategy()`. `Category` total 237 -> 238, `trend` bucket 58 -> 59 (`tests/test_altport2_ports.py::test_the_category_count_moved_by_exactly_three`, `tests/test_readme_counts.py`).
4. `pandas_ta/core.py` → `AnalysisIndicators.adxr` — the `df.ta.adxr()` accessor.
5. `tests/test_adxr.py` — 13 tests (correctness, causality mutant, scale, wiring).

`docs/IndicatorDictionary.md` regenerated (`python docs/gen_indicator_dictionary.py`):
`ADXR_14` tagged `SF` (scale-free, a bounded [0, 100] oscillator like `ADX_14`).
`docs/MLCompanionContract.md`'s measured-count sentence moved 570 -> 571 tagged
columns, 216 -> 217 `SF` (`tests/test_ml_companions.py`). README's headline moved
237 -> 238, the `trend` row 58 -> 59, and the `df.ta` accessor count 245 -> 246
(`tests/test_readme_counts.py`).

`docs/gate_e_ledger.csv` is **not** updated by this session, per the
issue-solver rule: the launcher runs Gate E after this session, and a later
receipt session records the ledger row with the measured numbers.
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails until then — expected, listed under Gate F above.

## To close

1. Launcher runs Gate E (`gate_e_overlap.py run --module pandas_ta.trend.adxr
   --name adxr`) and both repos' suites.
2. A receipt session reads the Gate E numbers, applies the `r3-perframe-0.90`
   bands, and either:
   - records the ledger row (`python docs/gate_e_ledger.py record ...`) and
     fills in the measured max \|ρ\|, comparator and sample size above — SHIP,
     DISCLOSE, or DISCLOSE_GAP; or
   - if STRUCK with no waiver: deletes `pandas_ta/trend/adxr.py`, its export,
     `Category` entry, accessor, `tests/test_adxr.py`, and reverts the README /
     `docs/IndicatorDictionary.md` / `docs/MLCompanionContract.md` / Gate E
     ledger counts this port moved — keeping this file as the receipt.
