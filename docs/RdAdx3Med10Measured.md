# Rolling Median of ADX(3) — measured (`rd_adx3_med10`)

PandasTa issue #171. Source: Reddit, tier 4 (ResearchIntel kb/reddit.db): r/quant
`rd:quant:1gc3o70` (2024-10-25), https://www.reddit.com/r/quant/comments/1gc3o70/ — "Use ADX with 3,
5, 8 periods. And then create the median of each of these for past 10 and 20 data points
respectively." Claimed use (tier 4, untested by the poster): extra ML features, poster claims a big
gain.

**Status: Gates A–E cleared. SHIP.** `rd_adx3_med10` is wired into `Category["trend"]` and stays.

Shipped: `pandas_ta/trend/rd_adx3_med10.py`, one column `RD_ADX3_MED10_{adx_length}_{length}`
(default `RD_ADX3_MED10_3_10`). Tests: `tests/test_rd_adx3_med10.py` (13). Numbers:
`python docs/measure_rd_adx3_med10.py` and `python docs/measure_rd_adx3_med10_cpu.py`. Environment:
Python 3.11.2, pandas 2.3.3, numpy 1.26.4. Measured 2026-11-26.

## This port ships exactly one of the issue's six named combinations

The poster's own words name six combinations: ADX at 3/5/8 periods, each median'd over 10 and 20
bars. Issue #171's title and "What" name exactly one of them — `rd_adx3_med10`, ADX(3) median'd over
10 bars — and that is what ships. The other five (ADX(5)/ADX(8) at both windows, and ADX(3) at 20)
are not this issue's scope; each would need its own issue if wanted.

## Gate A — the formula, read bar-by-bar

    ADX3            = adx(high, low, close, length=3)["ADX_3"]
    RD_ADX3_MED10    = ADX3.rolling(10).median()

`adx()` is this fork's own existing, already-ported, already-tested Average Directional Index
(`pandas_ta/trend/adx.py`, cites the TradingView "DMI ADX TREND 2.0" script in its own docstring).
This port re-uses that function rather than re-deriving ADX from scratch — the only new arithmetic is
the one `.rolling(10).median()` call on top of the already-shipped `ADX_3` column, identical in form
to `pandas_ta.statistics.median`'s own `close.rolling(length).median()`.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass | An independent recompute (calls this fork's own, already-tested `adx()` for `ADX_3`, then a plain `numpy.median` over NumPy slices — never the module's own `.rolling().median()` path for the outer statistic) matches the shipped column on 686 of 686 compared bars of a 700-bar synthetic OHLC walk, max\|diff\| 0.0 (exact). `length=1` reduces to the identity on `ADX_3` (695 of 695 compared bars equal), pinning that the median is a plain pass-through at a 1-bar window. |
| B Causality | pass | 9-offset future-perturbation sweep (whole tail from bar j onward scaled x1000): real module leaks at 0 of 9. A mutant (`importlib`-read source, the median's input shifted toward the future with `.shift(-1)` before the rolling call, `exec`'d in memory) is live (differs from the real module) and leaks at 5 of 9 — a MAJORITY, not all: a rolling median is robust to a single extreme input, so at a minority of offsets the perturbed value lands on the same side of the window's existing median and does not move it (see `tests/test_rd_adx3_med10.py::test_mutant_is_caught`'s own docstring). |
| C Reachability | pass | Synthetic: 900-bar OHLC walk (seed 11, σ=0.02): 886 of 900 finite (14-bar warm-up: ADX(3)'s own warm-up feeding straight into the 10-bar median window, since `min_periods` defaults to `length`), 538 distinct values, range [21.419409, 95.602225]. Ten independent 900-bar seeds: 886 non-NaN of 900 on every seed, 515–558 distinct values. Real data (run `is171-rd_adx3_med10-9b4dba1e`, 89 ALTPORT-1 BIST frames): 397,603 non-NaN of 398,849 pooled bars, all 397,603 non-zero (`overlap_max.csv` `non_nan` / `non_zero`); `degenerate.csv` empty, `n_degenerate` = 0. Known slack: `min_bars` (`adx_length + max(length, min_periods)` = 13) is one bar short of the true first-valid-bar warm-up (14), so a 13-14 bar frame can clear `verify_series` and return an all-NaN Series instead of `None`; left unfixed to avoid invalidating the sha1 this Gate E run is pinned to (`docs/gate_e_ledger.csv`) -- revisit at the next re-measure. |
| D Scale-free | pass | x8/x64 bit-identical on all 886 fired bars with matching NaN masks for both `ADX_3` and `RD_ADX3_MED10` (ADX's own formula divides directional movement by ATR, both linear in a joint positive price rescale, and a power-of-two `k` keeps that cancellation exact in IEEE float; a rolling MEDIAN of an unchanged series is itself unchanged, so no further error enters at the median step). x10/x3.7: `ADX_3` within 5.33e-13 / 4.48e-13, `RD_ADX3_MED10` within 3.06e-13 / 3.62e-13 (both well under the 1e-9 test tolerance, matching house convention -- `tests/test_rd_range100_pct500.py`'s own x10/x3.7 check), identical NaN masks. `0 < 886 < 900` fires, 538 distinct values (non-constant). Re-run clean with `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` (`docs/measure_rd_adx3_med10_cpu.py`): same 13/13 tests pass — no exact bit-count or digit beyond a stated tolerance is pinned, so the CPU-variant kernels on a GitHub runner cannot break this suite. |
| E Attribution | pass — SHIP | `RD_ADX3_MED10_3_10` max \|ρ\| **0.4656** vs `CHOP` (compute_all, n = 396,311); manifest max `0.4405` vs `BB_BWidth_Pctl` (n = 391,907); next comparator overall `chop` 0.4478 (compute_all, n = 397,455). Per-frame max median \|ρ\| **0.4791** vs `CHOP`, 0.0% of 89 frames ≥ 0.90. Both well under the 0.76 SHIP line (`r3-perframe-0.90` bands). 89 ALTPORT-1 frames, 398,849 pooled bars, 687 comparators (329 compute_all + 358 manifest), 0 degenerate columns, canary bit-equal (AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS). Run `is171-rd_adx3_med10-9b4dba1e`, recorded in `docs/gate_e_ledger.csv`, measured 2026-11-26. |
| F Suites | this repo only (per the porting rules, the launcher runs both whole suites) | `python -m pytest -q tests/test_rd_adx3_med10.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`: see "Final suite run" below. Whole suites: run by issue-solver in clean worktrees (see the PR body). |

## Wiring counts, read back

`Category` total 412 (was 411 on `dev`'s tip at this branch's base), `Category["trend"]` 69 (was 68).
README headline and the `trend (69)` row updated to match; `docs/IndicatorDictionary.md` regenerated
(414 indicators probed, this column's own row tagged `SF`, warm-up 14); `docs/MLCompanionContract.md`'s
running tally updated 756 → 757 tagged columns, 382 → 383 `SF`; `CATEGORY_TOTAL` 412 and
`CATEGORY_BUCKETS["trend"]` 69 in `tests/test_altport2_ports.py`.

## Final suite run

`python -m pytest -q tests/test_rd_adx3_med10.py tests/test_readme_counts.py
tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
— 1,695 passed, 7 skipped, 0 failed, measured 2026-11-26 (Gate E ledger row now recorded, so the
owed-row test passes). Re-run under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`
(`docs/measure_rd_adx3_med10_cpu.py`, this module only): 13 passed. Both repos' whole suites: run by
issue-solver in clean worktrees (see the PR body).

## Next step

None. Gates A–F cleared; `rd_adx3_med10` ships.
