# DX, Directional Movement Index, unsmoothed (14) — measured (`dx`)

jesse (MIT) `dx.py`:

    dx = 100 * |DI+ - DI-| / (DI+ + DI-)

Candidate `j_dx_14` from the 2026-10-24 library catalog screen round 2
(`docs/issues/screen/ind_screen_r2.py`, `docs/issues/screen/candidates_r2.csv`).
Issue #120 / J-DX-14.

**Status: Gates A-F cleared. Gate E SHIP: max |rho| 0.5871 vs `ADX`
(n=396,446), per-frame max median 0.5904 vs `ADX_Pctl`, 89 ALTPORT-1 frames
-> below the 0.76 SHIP line. Ledger row recorded 2026-10-31.**

Shipped: `pandas_ta/trend/dx.py`, one column `DX_<length>` (default `DX_14`),
range [0, 100]. Tests: `tests/test_dx.py` (13). Numbers:
`python docs/measure_dx_proxy.py`. Environment: pandas 2.3.3, numpy 1.26.4
(per `.github/workflows/ci.yml` pins), Python 3.11. Measured 2026-10-31.

## Design choice: built on this fork's own `adx()`, not re-derived

The round-2 prototype (`ind_screen_r2.py:38-51`) computes +DI/-DI from
scratch with its own `dm_wilder()`/`dx_wilder()` helpers (Wilder RMA
smoothing via `.ewm(alpha=1/n, adjust=False)`, ATR-normalized). This port
does not repeat that derivation: `pandas_ta.trend.adx.adx()` already
computes the same terms under the names `DMP_<length>`/`DMN_<length>`
(`k = scalar / atr_`, `dmp = k * ma(mamode, pos, length)`, same `pos`/`neg`
masks as the prototype's `pdm`/`mdm`, same RMA mamode by default), and
`adx()` builds its own internal, unexported `dx` variable from exactly
`scalar * (dmp - dmn).abs() / (dmp + dmn)` before smoothing that into
`ADX_<length>`. This port reads `DMP_<length>`/`DMN_<length>` off `adx()`'s
own returned frame and applies the source formula directly to them, rather
than transliterating the prototype's independent DI loop -- the same reuse
this fork already uses for `adxr()`. `adx()`'s own correctness is upstream
and out of scope for this port.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass | `test_matches_the_source_formula_recomposed_from_adx` (length 14 and 7): `dx()` output bit-identical to `100 * (dmp - dmn).abs() / (dmp + dmn)` computed independently in the test from `adx()`'s own `DMP_<length>`/`DMN_<length>` columns, on a 900-bar synthetic OHLC walk. `test_bounded_zero_to_hundred`: output in [0, 100] (a ratio of two non-negative terms, numerator <= denominator by construction). |
| B Causality | pass | Future-perturbation sweep, 15 offsets (60..830 step 55) on a 900-bar OHLC walk: real module leaks at 0/15 (`test_real_module_never_reads_the_future`). A look-ahead mutant (`importlib` source read, the `DMN_<length>` read rewritten to `.shift(-1)`, `exec`'d into a fresh in-memory module) is proved live (differs from the real module's output) and caught at 15/15 offsets (`test_future_read_mutant_is_caught`). |
| C Reachability | pass | 900-bar synthetic trending walk (seed 11, sigma=0.02): 886 of 900 bars finite (14-bar warm-up, inherited from `adx()`'s own RMA warm-up), 881 distinct values, range [0.013883, 62.153672]. Real data (Gate E run, 89 ALTPORT-1 frames, 398,849 pooled bars): 397,603 non-NaN, 397,603 non-zero (`overlap_max.csv` `non_nan`/`non_zero`). |
| D Scale-free | pass | x8 / x64 OHLC scaling: bit-identical, max \|diff\| 0.0 (DX is a ratio of two ADX-derived terms -- `scalar / atr_`, `(dmp - dmn).abs() / (dmp + dmn)` -- that cancel a price scale exactly, same as ADX itself). x10: max \|diff\| 2.877698e-13, well inside the 1e-9 tolerance pinned by `test_other_scales_within_tolerance`. `0 < 886 < 900` fires, plus 881 distinct values (`test_fires_on_real_shaped_data_and_is_not_constant`), so a constant column cannot pass. `test_too_short_a_series_returns_none` pins the other edge: a 10-bar series (below `length`) returns `None` rather than an all-NaN series. |
| E Attribution | **SHIP.** Port's own measurement, run `is120-dx-175e124e`: `DX_14` max \|rho\| 0.5871138 vs `ADX` (`compute_all`, n=396,446), per-frame max median 0.5904332 vs `ADX_Pctl` (89 frames, 0.0% of frames >= 0.90). 687 comparators (329 `compute_all` + 358 `ml_features` manifest), canary bit-equal (AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS). Below the 0.76 SHIP line of `r3-perframe-0.90` -> SHIP. Recorded in `docs/gate_e_ledger.csv` 2026-10-31. (Prototype's own number, 2026-10-24, was 0.5871 vs `ADX` against the prototype's independent `dx_wilder()` -- a coincidentally identical pooled max to this port's own measurement, not the same run.) |
| F Suites | this repo only | `python -m pytest -q`: 3 failed, 3514 passed, 83 skipped (2026-10-31), falling to 2 failed once the ledger row landed (`test_gate_e_ledger.py` now passes). The remaining two are pre-existing, neither naming `dx`: `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows` (needs the sibling `../AlternativeRepos` checkout, deselected in CI), `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` (CLAUDE.md's documented pre-existing break from `8d8f705`). Parent repo suite run by the launcher. |

## Wiring (five touch points)

1. `pandas_ta/trend/dx.py` — the indicator.
2. `pandas_ta/trend/__init__.py` — package export.
3. `pandas_ta/__init__.py` → `Category["trend"]` — discovery / `df.ta.strategy()`. `Category` total 248 -> 249, `trend` bucket 59 -> 60 (`tests/test_altport2_ports.py::test_the_category_count_moved_by_exactly_three`, `tests/test_readme_counts.py`).
4. `pandas_ta/core.py` → `AnalysisIndicators.dx` — the `df.ta.dx()` accessor.
5. `tests/test_dx.py` — 13 tests (correctness, causality mutant, scale, wiring).

`docs/IndicatorDictionary.md` regenerated (`python docs/gen_indicator_dictionary.py`):
`DX_14` tagged `SF` (scale-free, a bounded [0, 100] oscillator like `ADX_14`
and `ADXR_14`). `docs/MLCompanionContract.md`'s measured-count sentence
moved 581 -> 582 tagged columns, 227 -> 228 `SF` (`tests/test_ml_companions.py`).
README's headline moved 248 -> 249, the `trend` row 59 -> 60, and the
`df.ta` accessor count 256 -> 257 (`tests/test_readme_counts.py`).

`docs/gate_e_ledger.csv` recorded 2026-10-31: `dx:DX_14 SHIP 0.5871 vs ADX`.

## Open

Nothing open. Gates A-F cleared, Gate E ledger row recorded.
