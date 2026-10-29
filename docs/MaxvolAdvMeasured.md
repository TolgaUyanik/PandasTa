# maxvol_adv — measured

> **Status: gates measured (issue [#191](https://github.com/TolgaUyanik/PandasTa/issues/191)).**
> Gates A, B and D pass. Gate E was run on the port on 2026-10-29 and is SHIP, and the same run
> gives Gate C its real-data counts. Gate F shows no regressions in either repo, though neither
> suite is fully green on its own base (see Gate F). Merging is the owner's call.

`MAXVOLADV_14_50 = max(volume, last 14 bars) / SMA(volume, 50)`. Both windows end at, and include,
the current bar. The value is NaN where the ADV is ≤ 0. Module `pandas_ta/volume/maxvol_adv.py`,
tests `tests/test_maxvol_adv.py`, branch `B2-MAXVOL14-ADV50`.

## Source

Reddit, r/Daytrading 1tv21c0 (2026-06-02), https://www.reddit.com/r/Daytrading/comments/1tv21c0/
(tier 4, crowd talk). The poster lists "max_volume_vs_adv (peak volume day)" as a top-3 feature
of an XGBoost classifier (AUC 0.723) for 100-200% five-day moves in low-float stocks. That claim
is untested here. **The post gives only the feature name.** It does not fix the peak window, and
it does not say what ADV is. The 14-bar peak and ADV = SMA50(V), excluding nothing, are the
choices of the screen prototype: candidate `b2_maxvol14_adv50`,
`docs/issues/screen/ind_screen_r8.py:116-118`, on the owner's machine only (`docs/issues/` is
gitignored). It reads `sdiv(v.rolling(14).max(), mean(v, 50))`. Its helpers, at
`ind_screen.py:41-47`, define `mean` as `x.rolling(n).mean()` and `sdiv` as `a / b` with only
±inf mapped to NaN. Read on 2026-10-29, after the port was written, the prototype's values differ from the
port's in one case only: a negative ADV gives a finite ratio there and NaN here. Volume is never
negative, so real data cannot reach that case. A zero ADV gives NaN in both. One API difference
remains: a frame shorter than max(short, long) = 50 bars returns `None` here and an all-NaN
series there. Same post as
`range_compress_run`.

## Is it already shipped? (checked before porting, 2026-10-28)

**Not in pandas_ta.** A grep for rolling maxes and rolling means of volume in the package found
no rolling max of raw volume. The one rolling volume max is `pocket_pivot`'s, which is taken
over derived `sell_volume`. The rolling means it found are `vfi`'s `vave` (a lagged mean used as
a clip cutoff, with no max and not shipped as a column) and `fvg_sweep_magnet`'s internal
`volume / SMA20(volume)` (a gating input, not a shipped column). The nearest shipped columns are:

* `pvo` (`PVO_12_26_9`, `PVOs_12_26_9`): a percent difference of two EMAs of volume. It is
  smooth and has no max, so it is not a function of this column. The prototype's Gate E top
  comparator was `pvo_PVOs_12_26_9` at 0.7003.
* The engine's `VOL_RATIO` (`volume / SMA(volume, 20)`): one bar over the average, with no
  14-bar max and a different ADV length. It is cited from `tod_profile`'s docstring; the engine
  source was not read.
* `pocket_pivot`'s `PPIVOT_VOLRATIO`: up-volume over the largest prior *down*-volume bar. Both
  the numerator and the denominator differ.

None of these can be thresholded into this column, unlike #193 (see
`docs/EquivalentStrategies.md`). The engine's 687-column Gate E comparator pool was not
inspected before porting; Gate E on the port settled it (below). The top two comparators in
`top25.csv` are `pvo_PVOs_12_26_9` at 0.7003 and `pvo_PVO_12_26_9` at 0.5828.

## Gates

Environment for Gates A, B and D (the author's machine): `.venv-pd2` (pandas 2.3.3) and `.venv`
(pandas 3.0.6), Python 3.12. Gates C, E and F ran on the owner's machine: Python 3.11.9,
pandas 2.3.3, numpy 1.26.4. The synthetic
numbers come from `tests/test_maxvol_adv.py`: 1,200 bars of rounded lognormal(10, 0.6) volume,
seed 11.

| Gate | Result |
|---|---|
| A | No source formula exists to check against. The post names the feature, and the windows and the ADV come from the prototype, `ind_screen_r8.py:116-118` (see Source; same ratio, with one divergence that real data cannot reach). The port was checked against that definition: a hand-computed 5-bar sequence, an independent loop (rtol 1e-12), `short > long` (exact 4 / 3.5), the 49-bar warm-up, and a zero or negative ADV giving NaN rather than inf. One NaN volume bar blanks its own output and the next max(short, long) − 1 bars: 50 bars in all at the defaults, and 80 at `short=80`. `offset` and `fillna` are covered too. |
| B | Future perturbation at 31 offsets, using two futures (another walk, and the same walk ×1000). The real module leaks at 0 of 31. Two one-bar look-ahead mutants (`volume.shift(-1)` feeding the peak, and the same feeding the ADV) are each shown to change the output, then caught at 31 of 31. |
| C | Real data, from the Gate E run below (89 ALTPORT-1 BIST frames, 398,849 bars): 394,488 non-NaN, 394,466 non-zero. The 4,361 NaN bars equal 89 × 49, the warm-up, so no NaN-volume blanking occurred. With volume never negative, the 22 zeros can only be bars whose 14-bar window traded nothing while the 50-bar ADV was still positive (this follows from the formula; the bars were not inspected). Synthetic: 1,151 non-NaN bars, 1,151 distinct values, range 1.129 to 7.358. |
| D | The column reads no price. Volume ×8 and ×64 are bit-identical. ×10 and ×3.7 differ by at most 2.2e-16 and 3.9e-16 relative (max \|Δ\| / \|base\|). NaN masks match in all four. The column is continuous, so `0 < fires < n` is replaced by nunique = 1,151 of 1,151 non-NaN bars (see C). |
| E | **SHIP** (measured on the port 2026-10-29, 89 frames, 398,849 bars, 687 comparators, canary bit-equal): max \|ρ\| 0.7003 vs `pvo_PVOs_12_26_9` (n = 394,488), top-5 per-frame median 0.7451 vs the same column. Same numbers as the prototype. Recorded in `docs/gate_e_ledger.csv` from run `gatecheck-20261029-maxvol_adv-r2`. That run was made after this module's docstring was edited and gave the same numbers as the first run, `gatecheck-20261029-maxvol_adv`. Both runs are in `MultipleBranchWork/Backtesting-adhoc-gatee-agent/backtest_results/gatee/` on the owner's machine: Backtesting `91ab7ae2`, stamp `engine_code` `f58eb5da`, `pandas_ta_src_sha1` `8a2d3e46`. To re-run, from `../Backtesting/Backtesting`: `python scripts/analysis/gate_e_overlap.py run --module pandas_ta.volume.maxvol_adv --name <run name>`. Outputs land in `../backtest_results/gatee/<run name>/`. |
| F | **No regressions** in either repo; neither suite is green on its own base. See below. |

### Gate F (re-measured 2026-10-29 on the owner's machine, at this branch's head)

**No regressions in either repo.** Neither suite is fully green on its own base, so this rests
on the failing node IDs matching, not on a zero.

* **This repo** (Python 3.11.9, pandas 2.3.3, numpy 1.26.4): 2 failed, 3258 passed, 83 skipped.
  The two failures are the tests CI deselects by name:
  * `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`, the known break in
    CLAUDE.md;
  * `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`, which needs
    the sibling `../AlternativeRepos/pandas-ta-classic` checkout.

  The `test_wilder_rma.py` failure of the earlier run is gone, because `dev` fixed it in
  `cda43e3`. CI on `2f05b20` (run 40863800069) was green: 3258 passed, 83 skipped, 2 deselected.
* **Backtesting** (`tests/`, Backtesting `91ab7ae2`): 16 failed, 1584 passed, 14 skipped and
  4 errors with this branch's `pandas_ta`, and exactly the same with `dev`'s (`d7fd91d`, whose
  `pandas_ta/` matches `6df7539`). The 20 failing node-id lists are identical:
  `test_build_strategy_master.py` 8, `test_strategy_loader.py` 6, `test_spmine_golden.py` 5,
  `test_exit_no_drift.py` 1. All 20 fail on `dev`'s code too. Each run printed the tree it
  imported. The dev run imported `D:\AwakenAnalytics\PandasTa\pandas_ta` (tree sha1 `efca0690`,
  the value on the other ledger rows). The branch run imported
  `...\PandasTa-197-maxvol-adv\pandas_ta` (tree sha1 `8a2d3e46`, the value in the Gate E r2 run's
  `meta.json`).

The earlier measurement (2026-10-28, base `d7fd91d`, the author's machine) also found no
regressions in this repo. On `.venv` (pandas 3.0.6) it had 42 failed / 3161 passed with the change
and 42 failed / 3147 passed without it, with identical failing lists. Those 42 pandas-3 failures
predate this port, and pandas 3 was not re-run here.

## Dictionary row provenance

`docs/IndicatorDictionary.md` was hand-patched, as the header there explains. The row was copied
verbatim from `.venv-pd2/bin/python docs/gen_indicator_dictionary.py <scratch>` (pandas 2.3.3,
no TA-Lib; the rest of that output was discarded because it empties `cdl_pattern`):

```
| `maxvol_adv` | V | `short=None`, `long=None` | `MAXVOLADV_14_50` SF | 49 | The largest single-bar volume of the last `short` bars, divided by the average volume of the last `long` bars (ADV). 1 means the peak bar was an… |
```

The same run's header counts were 239 probed, 237 in `Category`, 245 callable as `df.ta`, and
volume (25).
