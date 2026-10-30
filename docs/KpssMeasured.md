# kpss — measured

> **Status: Gates A, B and D pass; C and E are owed (issue [#157](https://github.com/TolgaUyanik/PandasTa/issues/157)).**
> Gate E and Gate C's real-data counts need the private Backtesting engine and the BIST cache,
> which the author's machine does not have. Until a Gate E run is recorded in
> `docs/gate_e_ledger.csv`, `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
> fails on this branch, and that is the only failure (see Gate F). Merging is the owner's call.

`KPSS_100` is the KPSS statistic (Kwiatkowski, Phillips, Schmidt and Shin, 1992) of log close over
the last 100 bars, under the trend-stationary null (`regression="ct"`), with a one-lag Bartlett
long-run variance. Small values mean price stayed near a straight line. Large values mean it
drifted away from one, the way a random walk does. The 5% critical value is 0.146 and the 1% is
0.216. Module `pandas_ta/statistics/kpss.py`, tests `tests/test_kpss.py`, branch
`issue-157-kpss`.

## Source

Kats tsfeatures (Meta, MIT), `get_unitroot_kpss`, which returns
`statsmodels.tsa.stattools.kpss(x, regression="ct", nlags=1)[0]`. Kats follows Hyndman's
tsfeatures. statsmodels implements eqs. 10–11, pp. 164–165, of Kwiatkowski et al. (1992),
*J. Econometrics* 54. Kats applies the statistic to a whole series. The 100-bar window and log
close as the input are the choices of the 2026-10-25 screen prototype: candidate
`kats_kpss_100`, `docs/issues/screen/ind_screen_r5.py`, which exists only on the owner's machine
(`docs/issues/` is gitignored). The prototype was not read for this port. Gate A runs against the
source call itself.

**Port vs. source, one deliberate difference in the arithmetic.** statsmodels detrends `x` with
`OLS(x, [1, t])`. The port detrends `log(close / close[window start])`, the same series shifted by
a constant that the intercept absorbs, using closed-form centred sums. The two agree to 2.2e-12
relative (Gate A). The shift is what makes the column bit-identical under ×8 and ×64 (Gate D).
`log(8c) = log(c) + log(8)` rounds differently on every bar, while `8c / 8c0 = c / c0` is exact.

## Is it already shipped? (checked before porting, 2026-10-30)

**Not in pandas_ta.** A grep of `pandas_ta/` for `stationar`, `unit root`, `adfuller`, `hurst` and
`variance_ratio` finds only `pandas_ta/ml/companions.py`, where the word appears in a comment and
a keyword about non-stationary *inputs*. No shipped column estimates persistence or stationarity.
Issue #4 (HLIFE) records the same absence in the parent engine (`hurst|halflife|autocorr|persist`
→ 0 columns). The issue's prototype measurements, quoted and not re-run here, are: fork overlap
max |ρ| 0.2091 vs `ichimoku_ml:ICHI_TK_CROSS_AGE` (12 frames), and Gate E max |ρ| 0.2256 vs
`ICHI_TK_CROSS_AGE` (n = 390,038, run `screen_r5_20261025`).

⚠ **Ties.** Issue #4 blocks `hurst`, `variance_ratio` and a rolling ADF until HLIFE-3 reports, and
its rule is to measure the persistence family against its survivor. KPSS is the same family, and
the issue (#157) names no such tie. Whether KPSS should also be measured against HLIFE's survivor
once one exists is the owner's call.

## Gates

Environment for Gates A, B and D: the author's machine, Windows, Python 3.13.14. Two venvs:
`.venv-pd2` with pandas 2.3.3, numpy 2.5.4, TA-Lib 0.7.1 and statsmodels 0.15.0, and `.venv`
with pandas 3.0.0 and numpy 2.4.2, without statsmodels. The synthetic numbers come from
`tests/test_kpss.py`: 1,200 bars of a geometric random walk, σ = 1.5%, rounded to 0.01, seed 11.

| Gate | Result |
|---|---|
| A | **Against the source call:** `statsmodels.tsa.stattools.kpss(x, regression="ct", nlags=1)[0]` on every window of an 800-bar walk (seed 3). Max relative difference 2.2e-12 at length 100 and 1.0e-12 at length 30. statsmodels is not a CI dependency, so this test skips in CI. **In CI:** an independent `np.linalg.lstsq` loop written from eqs. 10–11 (rtol 1e-9 at lengths 100, 30 and 3), and a hand-computed window with its arithmetic in the test (`exp([0, 1, 0, 2])`, length 4 → 0.25). **Behaviour:** over 200 synthetic 100-bar windows each, a random walk reads median 0.599 and exceeds 0.146 in 200 of 200. An AR(0.5) around a linear trend reads median 0.112 and still exceeds 0.146 in 33% of windows. One Bartlett lag under-corrects autocorrelation of 0.5 by that much. This is a property of the source's `nlags=1`, not a port defect, and a model reading this column sees it as a level, not as a test decision. **Edges:** a flat window (zero residual variance) is NaN, not inf. A zero or negative close blanks the windows that contain it. A NaN close blanks its own bar and the next 99 (100 in all). The warm-up is 99 bars. `offset` and `fillna` are covered. |
| B | Future perturbation at 31 offsets, with two futures (another walk, and the same walk ×1000). The real module leaks at 0 of 31. Two one-bar look-ahead mutants (`importlib` source read, `exec`'d in memory) are each shown to change the output, then caught at 31 of 31: the output written one bar early (`values[length - 2:-1]`), and the window read one bar ahead. There is no recursive stage, so the taint reach is exactly the 100-bar window. |
| C | **Owed.** Real-data firing counts come from the Gate E run. Synthetic: 1,101 non-NaN bars, 1,101 distinct values, none zero, range 0.0865 to 1.0744. |
| D | Close ×8 and ×64 are bit-identical. ×10 and ×3.7 differ by at most 1.08e-14 and 8.54e-15 relative (max \|Δ\| / \|base\|). NaN masks match in all four. The column is continuous, so `0 < fires < n` is replaced by nunique = 1,101 of 1,101 non-NaN bars (see C). |
| E | **Owed.** To run, from `../Backtesting/Backtesting`: `python scripts/analysis/gate_e_overlap.py run --module pandas_ta.statistics.kpss --name <run name>`, then record it with `python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD`. The prototype's number (max \|ρ\| 0.2256, SHIP) is not a measurement of this port. |
| F | **No regressions in this repo** (below). Backtesting not run. |

### Gate F (2026-10-30, the author's machine, `.venv-pd2`)

Run with CI's two `--deselect`s:

* `dev` at `9b964a8`: 0 failed, 3258 passed, 83 skipped.
* this branch: 1 failed, 3276 passed, 83 skipped. The +18 passes are `tests/test_kpss.py`.

The one failure is `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, for
`kpss`, and it clears when the Gate E row lands. Without the deselects, `dev` also fails exactly
the two tests CI deselects, which matches CI.

## Dictionary row provenance

`docs/IndicatorDictionary.md` was **fully regenerated**, not hand-patched, with
`.venv-pd2/Scripts/python docs/gen_indicator_dictionary.py` (pandas 2.3.3, numpy 2.5.4, TA-Lib
0.7.1). TA-Lib was present, so `cdl_pattern` kept every column. The whole diff against `dev` is
the `kpss` row, the counts (240 probed, 238 in `Category`, 246 callable as `df.ta`, statistics
(13)), `kpss` in the *Feed-ready shortlist*, the probe date, the numpy version in *Known breaks*,
and the removal of the header notes about hand-patched rows. The `pfe`, `kalman_trend`,
`range_compress_run`, `dpo` and `maxvol_adv` rows those notes covered came out byte-identical to
the patched ones.

`docs/indicators/kpss.md` was not generated. `docs/gen_indicator_pages.py` reads Gate E runs from
`../Backtesting`, which is absent here, so on this machine it rewrites 49 unrelated pages and
marks `fvg` as unmeasured. The last four ports (`pfe`, `kalman_trend`, `range_compress_run`,
`maxvol_adv`) have no page either.
