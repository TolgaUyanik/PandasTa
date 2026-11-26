# Rolling Median of ADX(8) — measured (`rd_adx8_med20`)

PandasTa issue #178. Source: Reddit, tier 4 (ResearchIntel kb/reddit.db): r/quant
`rd:quant:1gc3o70` (2024-10-25), https://www.reddit.com/r/quant/comments/1gc3o70/ — "Use ADX with 3,
5, 8 periods. And then create the median of each of these for past 10 and 20 data points
respectively." Claimed use (tier 4, untested by the poster): extra ML features, poster claims a big
gain.

**Status: Gates A–D cleared this session. Gate E: pending, run by issue-solver after this
session.** `rd_adx8_med20` is wired into `Category["trend"]`; `tests/test_gate_e_ledger.py
::test_every_indicator_that_needs_a_row_has_one` fails until the ledger row is recorded — expected,
not a defect (see CLAUDE.md "Owed, not failed, on the way to `dev`").

Shipped: `pandas_ta/trend/rd_adx8_med20.py`, one column `RD_ADX8_MED20_{adx_length}_{length}`
(default `RD_ADX8_MED20_8_20`). Tests: `tests/test_rd_adx8_med20.py` (14). Numbers:
`python docs/measure_rd_adx8_med20.py` and `python docs/measure_rd_adx8_med20_cpu.py`. Environment:
Python 3.11.2, pandas 2.3.3, numpy 1.26.4. Measured 2026-11-26.

**Round-1 review fix, same session.** An earlier draft's `min_bars = adx_length + max(length,
min_periods)` (= 28 for the defaults) under-counted ADX's own warm-up: `ADX_8`'s first non-NaN value
sits at index 15 of a longer series (measured), so a 28..35-bar input passed `verify_series`'s guard
but could never produce a single non-NaN median -- it would have come back as an all-NaN `Series`
instead of `None`. Fixed to `min_bars = 2 * adx_length + max(length, min_periods)` (= 36), matching
the house convention already used for the same quantity in `adxr.py` (`verify_series(high, 2 *
length)`) rather than the tighter 35-bar bound; `tests/test_rd_adx8_med20.py::test_min_bars_boundary`
pins both the rejection at 27/35 bars and a finite result at 36. The fix does not change any
already-measured number below (866 fires, 481 distinct values, the Gate D diffs) -- it only changes
the guard's own threshold, which the 900-bar measurement frame was always well past. Also tightened
`test_mutant_is_caught`'s assertion from `>=` to `>` (the loose form reintroduced a majority-vs-tie
ambiguity issue #171's own sibling port had already closed), and stated the mutant's measured 5-of-9
catch ratio directly in that test's docstring instead of an extra indirection through this file.

## This port ships exactly one of the issue's six named combinations

The poster's own words name six combinations: ADX at 3/5/8 periods, each median'd over 10 and 20
bars. Issue #178's title and "What" name exactly one of them — `rd_adx8_med20`, ADX(8) median'd over
20 bars — and that is what ships. Issue #171 already shipped `rd_adx3_med10` (ADX(3), median 10);
this port is the sibling at the issue's other named length pair. The remaining four combinations
(ADX(3)/ADX(5) at 20, ADX(5)/ADX(8) at 10) are not this issue's scope; each would need its own issue
if wanted.

## Gate A — the formula, read bar-by-bar

    ADX8            = adx(high, low, close, length=8)["ADX_8"]
    RD_ADX8_MED20    = ADX8.rolling(20).median()

`adx()` is this fork's own existing, already-ported, already-tested Average Directional Index
(`pandas_ta/trend/adx.py`, cites the TradingView "DMI ADX TREND 2.0" script in its own docstring).
This port re-uses that function rather than re-deriving ADX from scratch — the only new arithmetic is
the one `.rolling(20).median()` call on top of the already-shipped `ADX_8` column, identical in form
to `pandas_ta.statistics.median`'s own `close.rolling(length).median()`, and to issue #171's own
`rd_adx3_med10` module.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass | An independent recompute (calls this fork's own, already-tested `adx()` for `ADX_8`, then a plain `numpy.median` over NumPy slices — never the module's own `.rolling().median()` path for the outer statistic) matches the shipped column on 866 of 866 compared bars of a 900-bar synthetic OHLC walk, max\|diff\| 0.0 (exact). `length=1` reduces to the identity on `ADX_8` (885 of 885 compared bars equal), pinning that the median is a plain pass-through at a 1-bar window. |
| B Causality | pass | 9-offset future-perturbation sweep (whole tail from bar j onward scaled x1000): real module leaks at 0 of 9. A mutant (`importlib`-read source, the median's input shifted toward the future with `.shift(-1)` before the rolling call, `exec`'d in memory) is live (differs from the real module) and leaks at 5 of 9 — a MAJORITY, not all: a rolling median is robust to a single extreme input, so at a minority of offsets the perturbed value lands on the same side of the window's existing median and does not move it (same measured ratio as issue #171's `rd_adx3_med10`, see `tests/test_rd_adx8_med20.py::test_mutant_is_caught`'s own docstring). |
| C Reachability | pass | Synthetic: 900-bar OHLC walk (seed 11, σ=0.02): 866 of 900 finite (34-bar warm-up: ADX(8)'s own warm-up feeding straight into the 20-bar median window, since `min_periods` defaults to `length`), 481 distinct values, range [13.679662, 50.250773]. Ten independent 900-bar seeds: 866 non-NaN of 900 on every seed, 471–524 distinct values. Real-data reachability: owed with Gate E. |
| D Scale-free | pass | x8/x64 bit-identical on all 866 fired bars with matching NaN masks for both `ADX_8` and `RD_ADX8_MED20` (ADX's own formula divides directional movement by ATR, both linear in a joint positive price rescale, and a power-of-two `k` keeps that cancellation exact in IEEE float; a rolling MEDIAN of an unchanged series is itself unchanged, so no further error enters at the median step). x10/x3.7: `ADX_8` within 1.99e-13 / 1.28e-13, `RD_ADX8_MED20` within 1.14e-13 / 1.21e-13 (both well under the 1e-9 test tolerance, matching house convention — `tests/test_rd_adx3_med10.py`'s own x10/x3.7 check), identical NaN masks. `0 < 866 < 900` fires, 481 distinct values (non-constant). Re-run clean with `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` (`docs/measure_rd_adx8_med20_cpu.py`): same 14/14 tests pass — no exact bit-count or digit beyond a stated tolerance is pinned, so the CPU-variant kernels on a GitHub runner cannot break this suite. |
| E Attribution | **pending** | Gate E: pending, run by issue-solver after this session. |
| F Suites | this repo only (per the porting rules, the launcher runs both whole suites) | `python -m pytest -q tests/test_rd_adx8_med20.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`: see "Final suite run" below. Whole suites: run by issue-solver in clean worktrees (see the PR body). |

## Wiring counts, read back

`Category` total 415 (was 414 on `dev`'s tip after this branch was rebased onto it, which had
picked up other PRs including issue #179's `rd_std_ratio_20_60` meanwhile), `Category["trend"]`
70 (was 69, unaffected by #179 since that port is `volatility`). README headline (415) and the
`trend (70)` row updated to match; `docs/IndicatorDictionary.md` regenerated (this column's own
row tagged `SF`, warm-up 34); `docs/MLCompanionContract.md`'s running tally updated 759 → 760
tagged columns, 385 → 386 `SF` (both already at 759/385 post-rebase from #179's own bump);
`CATEGORY_TOTAL` 415 and `CATEGORY_BUCKETS["trend"]` 70 in `tests/test_altport2_ports.py`.

## Final suite run

`python -m pytest -q tests/test_rd_adx8_med20.py tests/test_readme_counts.py
tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
— 1,712 passed, 7 skipped, 1 failed (`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
— expected, Gate E owed), measured 2026-11-27 (re-measured after the launcher's rebase onto `dev`
picked up other merged PRs). Re-run under
`NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` (`docs/measure_rd_adx8_med20_cpu.py`, this
module only): 14 passed. Both repos' whole suites: run by issue-solver in clean worktrees (see the
PR body).

## Next step

Gate E run owed: `../Backtesting/Backtesting/scripts/analysis/gate_e_overlap.py run --module
pandas_ta.trend.rd_adx8_med20 --name rd_adx8_med20`, then
`python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD`. A later receipt session
records the ledger row and the measured Gate E numbers in this file.
