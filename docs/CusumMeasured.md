# cusum — measured

> **Status: Gates A, B and D pass; C and E are owed (issue [#16](https://github.com/TolgaUyanik/PandasTa/issues/16)).**
> Gate E and Gate C's real-data counts need the private Backtesting engine and the BIST cache,
> which the author's machine does not have. Until a Gate E run is recorded in
> `docs/gate_e_ledger.csv`, `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
> fails on this branch, and that is the one failure (see Gate F). Merging is the owner's call.

`CUSUM_100` is the Chu-Stinchcombe-White CUSUM statistic on log close, with the supremum taken over
the last 100 reference bars. For each reference bar `n`, the log change from `n` to the current bar
`T` is divided by the window's one-bar volatility times `sqrt(T - n)`; the column is the largest of
those 100 values. Large positive values mean price has risen from some recent level faster than its
volatility explains. Module `pandas_ta/statistics/cusum.py`, tests `tests/test_cusum.py`, branch
`issue-16-cusum`.

## Source

Lopez de Prado, *Advances in Financial Machine Learning* (2018), ch. 17 *Structural Breaks*, the
Chu-Stinchcombe-White CUSUM test on levels, which the issue cites:

    S_{n,t} = (y_t - y_n) / (sigma_t * sqrt(t - n)),   sigma_t^2 = (t - 1)^-1 * sum_{i=2..t} (y_i - y_{i-1})^2
    S_t = sup_{n in [1, t]} S_{n,t},                     y = log price

The formula above is the one this port implements and tests against. It was written from the
chapter as cited; the book was not re-opened for this port, and there is no public reference
implementation that was run. Checking it against ch. 17 is a cheap step for the owner.

**Port vs. source, two deliberate differences.**

1. **Rolling window (the issue's decision).** The book's supremum runs over every earlier bar,
   which is O(n²) over a series and makes the column depend on where the series starts. The port
   takes it over the last `length` reference bars (`n = T - length .. T - 1`) and estimates
   `sigma` from the `length` one-bar log returns in that same window. Bar `T` reads closes
   `T - length .. T`. Default `length = 100`. The 100 is a choice, not a measurement; it matches
   the 100-bar window of the screen family (`kpss`, `lean_hurst_100`).
2. **Log differences as the log of a ratio.** `y_t - y_n` is computed as `log(close_t / close_n)`.
   The value is the same to rounding (Gate A: 5.5e-13 at most), and the ratio is what makes the
   column bit-identical under ×8 and ×64 (Gate D).

One-sided, as in the book: the column measures upward departures only. A downward mirror (the
infimum) would be a second column and a second Gate E row; it is not shipped here.

A property worth knowing: by Cauchy-Schwarz, `|y_t - y_n| <= sqrt(t - n) * sqrt(length) * sigma`,
so `|CUSUM| <= sqrt(length)` (10 at the default). A flat window followed by one move hits that
bound exactly.

## Is it already shipped? (checked before porting, 2026-10-30)

**Not in pandas_ta.** A grep of the repo (excluding the untracked `docs/pine/`) for `cusum`,
`stinchcombe` and `structural break` finds only the `atr_push` docstring's "structural
breakout", which is a price-level breakout rule, not this test. No structural-break statistic is
shipped. Shipped columns that this one may overlap on real data, because without the
`sqrt(t - n)` weights the supremum over `n` of `y_t - y_n` would be the log distance above the
window's low: position-in-range oscillators (`stoch`,
`willr`), `zscore`, and the trend-persistence columns `cti` and `er`. How much it overlaps any of
them is what Gate E measures; nothing was measured here. Issue #16 found no overlap in the fork or
the manifest; that was a search, not a correlation.

⚠ **Ties.** Issue #16 says CUSUM is persistence-adjacent: #4 (HLIFE) blocks `hurst`,
`variance_ratio` and a rolling ADF until HLIFE-3 reports, CUSUM is not on that list, but it should
also be measured against HLIFE's survivor once one exists. HLIFE has no survivor yet (#4 is
waiting on its own Gate E), so that comparison is owed. `kpss` (#157, PR #209, not merged) is in
the same family; whichever of the two merges second should be measured against the other.

## Gates

Environment for Gates A, B and D: the author's machine, Windows, Python 3.13.14. Two venvs:
`.venv-pd2` with pandas 2.3.3, numpy 2.5.4 and TA-Lib 0.7.1, and `.venv` with pandas 3.0.0 and
numpy 2.4.2. `tests/test_cusum.py` passes in both: 17 of 17. The synthetic numbers come from
`tests/test_cusum.py`: 1,200 bars of a geometric random walk, σ = 1.5%, rounded to 0.01, seed 11.

| Gate | Result |
|---|---|
| A | **Against the source formula:** the formula above written literally (nested Python loops on log levels, `y_t - y_n` as a difference of logs) on every window of a 400-bar walk. Max absolute difference 4.7e-14 at length 100, 4.8e-14 at 30, 5.5e-13 at 2; NaN masks identical. Asserted with rtol 1e-9, atol 1e-11. **Hand-computed:** `exp([0, 1, 0, 2])`, length 3 → √2, arithmetic in the test. **Bound:** `\|CUSUM\| <= sqrt(length)` over 80 walks (lengths 2, 5, 30, 100, 20 seeds each); a flat window then one move reads exactly 10.0 at length 100. **Behaviour:** 200 pairs of 101-bar walks (σ = 1%) sharing their noise, one with +0.5% per bar added to its last 20 returns: median 1.349 without the break, 2.823 with it, and the break reads higher in 200 of 200 pairs. **Edges:** a flat window (zero volatility) is NaN, not inf. A zero or negative close blanks the windows that contain it. A NaN close blanks its own bar and the next 100 (101 in all, since a window is `length + 1` closes). The warm-up is 100 bars. `length` below 2 falls back to 100. `offset` and `fillna` are covered. **Memory:** all windows are held at once, about 8·n·length bytes per intermediate array; the docstring says so. |
| B | Future perturbation at 31 offsets, with two futures (another walk, and the same walk ×1000). The real module leaks at 0 of 31. Two one-bar look-ahead mutants (`importlib` source read, `exec`'d in memory) are each shown to change the output, then caught at 31 of 31: the output written one bar early (`values[length - 1:-1]`), and the window read one bar ahead. There is no recursive stage, so the taint reach is exactly the `length + 1`-close window. |
| C | **Owed.** Real-data counts come from the Gate E run. Synthetic: 1,100 non-NaN bars, 1,100 distinct values, none zero, 27 negative, range -0.737 to 3.771. |
| D | Close ×8 and ×64 are bit-identical. ×10 and ×3.7 differ by at most 1.6e-14 and 1.7e-14 absolute; the test asserts ≤ 1e-12. Absolute, not relative, because the column crosses zero. NaN masks match in all four. The column is continuous, so `0 < fires < n` is replaced by nunique = 1,100 of 1,100 non-NaN bars (see C). |
| E | **Owed.** From `../Backtesting/Backtesting`, with `issue-16-cusum` checked out as the PandasTa sibling (`record` checks the run's `pandas_ta_src_sha1` against this tree): `python scripts/analysis/gate_e_overlap.py run --module pandas_ta.statistics.cusum --name <run name>`, then `python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD`. No prototype measurement exists for this candidate. |
| F | **No regressions in this repo** (below). Backtesting not run. |

### Gate F (2026-10-30, the author's machine, `.venv-pd2`)

Run with CI's two `--deselect`s:

* `dev` at `9b964a8`: 0 failed, 3258 passed, 83 skipped.
* this branch: 1 failed, 3275 passed, 83 skipped. The +17 passes are `tests/test_cusum.py`.

The one failure is `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, for
`cusum`, and it clears when the Gate E row lands.

## Dictionary row provenance

`docs/IndicatorDictionary.md` was **fully regenerated**, not hand-patched, with
`.venv-pd2/Scripts/python docs/gen_indicator_dictionary.py` (pandas 2.3.3, numpy 2.5.4, TA-Lib
0.7.1). The diff against `dev` (`git diff origin/dev -- docs/IndicatorDictionary.md`, enumerated
line by line on 2026-10-30) is:

* the `cusum` row (`CUSUM_100` SF, warm-up 100);
* the counts: 240 probed, 238 in `Category`, 246 callable as `df.ta`, statistics (13);
* the *Feed-ready shortlist* gains two entries, `cusum` and `range_compress_run`. The second is
  not this port's: the 2026-10-26 hand-patch added the `range_compress_run` row but not its
  shortlist entry, and the regeneration fills that gap (PR #209 does the same);
* the probe date, and the numpy version in *Known breaks*;
* the removal of the header notes about hand-patched rows, because the rows they covered (`pfe`,
  `kalman_trend`, `range_compress_run`, `dpo`, `maxvol_adv`) came out unchanged.

`docs/MLCompanionContract.md` follows the dictionary: 571 tagged columns, 217 `SF`.

**Conflict with PR #209.** `kpss` changes the same counts and dictionary lines. Whichever PR
merges second must rebase, regenerate the dictionary, and take the counts to 239 / 247 / statistics
(14) / 572 / 218 `SF` and `CATEGORY_TOTAL = 239`. `cusum` is wired on lines `kpss` does not touch
(end of the `Category` statistics list, end of `statistics/__init__.py`, before `entropy` in
`core.py`), so only the counters and the dictionary conflict.

`docs/indicators/cusum.md` was not generated. `docs/gen_indicator_pages.py` reads Gate E runs from
`../Backtesting`, which is absent here, so on this machine it rewrites unrelated pages.
