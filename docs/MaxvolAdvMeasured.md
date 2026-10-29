# maxvol_adv — measured

> **Status: NOT DONE. Do not merge to `main`.** The issue is done when the port has
> passed Gates A–F, or has been measured and reverted. Gates A, B and D pass. Gate E was run
> on the port on 2026-10-29 and is SHIP; the same run gives Gate C its real-data counts. Gate F
> is not met: the Backtesting suite was not run.

`MAXVOLADV_14_50 = max(volume, last 14 bars) / SMA(volume, 50)`. Both windows end at, and include,
the current bar. The value is NaN where the ADV is ≤ 0. Module `pandas_ta/volume/maxvol_adv.py`,
tests `tests/test_maxvol_adv.py`, branch `B2-MAXVOL14-ADV50`.

## Source

Reddit, r/Daytrading 1tv21c0 (2026-06-02), https://www.reddit.com/r/Daytrading/comments/1tv21c0/
(tier 4, crowd talk). The poster lists "max_volume_vs_adv (peak volume day)" as a top-3 feature
of an XGBoost classifier (AUC 0.723) for 100-200% five-day moves in low-float stocks. That claim
is untested here. **The post gives only the feature name.** It does not fix the peak window, and
it does not say what ADV is. The 14-bar peak and ADV = SMA50(V), excluding nothing, are the
choices of the screen prototype (candidate `b2_maxvol14_adv50` in
`docs/issues/screen/ind_screen_r8.py`), and they are known here only from the issue text. That
file is not on this machine and was not read, so the port was **not** compared with the
prototype line by line. Same post as `range_compress_run`.

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
`docs/EquivalentStrategies.md`). The engine's 687-column Gate E comparator pool was **not**
inspected. Gate E on the port is what settles whether something there restates this column.

## Gates

Environment: `.venv-pd2` (pandas 2.3.3) and `.venv` (pandas 3.0.6), Python 3.12. The synthetic
numbers come from `tests/test_maxvol_adv.py`: 1,200 bars of rounded lognormal(10, 0.6) volume,
seed 11.

| Gate | Result |
|---|---|
| A | No source formula exists to check against. The post names the feature, and the windows and the ADV come second-hand from the prototype (see Source). The port was checked against that definition: a hand-computed 5-bar sequence, an independent loop (rtol 1e-12), `short > long` (exact 4 / 3.5), the 49-bar warm-up, a zero or negative ADV giving NaN rather than inf, one NaN volume bar blanking exactly the next 50 output bars, `offset` and `fillna`. |
| B | Future perturbation at 31 offsets, using two futures (another walk, and the same walk ×1000). The real module leaks at 0 of 31. Two one-bar look-ahead mutants (`volume.shift(-1)` feeding the peak, and the same feeding the ADV) are each shown to change the output, then caught at 31 of 31. |
| C | Real data, from the Gate E run below (89 ALTPORT-1 BIST frames, 398,849 bars): 394,488 non-NaN, 394,466 non-zero. The 4,361 NaN bars equal 89 × 49, the warm-up, so no NaN-volume blanking occurred. Synthetic: 1,151 non-NaN bars, 1,151 distinct values, range 1.129 to 7.358. |
| D | The column reads no price. Volume ×8 and ×64 are bit-identical. ×10 and ×3.7 differ by at most 2.2e-16 and 3.9e-16 relative (max \|Δ\| / \|base\|). NaN masks match in all four. The column is continuous, so `0 < fires < n` is replaced by nunique = 1,151 of 1,151 non-NaN bars (see C). |
| E | **SHIP** (measured on the port 2026-10-29, run `gatecheck-20261029-maxvol_adv`, 687 comparators, canary bit-equal): max \|ρ\| 0.7003 vs `pvo_PVOs_12_26_9` (n = 394,488), top-5 per-frame median 0.7451 vs the same column. Same numbers as the prototype. Recorded in `docs/gate_e_ledger.csv`. To re-run, from `../Backtesting/Backtesting`: `python scripts/analysis/gate_e_overlap.py run --module pandas_ta.volume.maxvol_adv --name maxvol_adv`. |
| F | **Not met.** See below. |

### Gate F, this repo (measured 2026-10-28, base `d7fd91d`)

| venv | clean `d7fd91d` | with this change |
|---|---|---|
| `.venv-pd2` (pandas 2.3.3) | 2 failed, 3187 passed, 86 skipped | 2 failed, 3201 passed, 86 skipped |
| `.venv` (pandas 3.0.6) | 42 failed, 3147 passed, 86 skipped | 42 failed, 3161 passed, 86 skipped |

The clean run had every change stashed, untracked files included. In both venvs the failing
node-id lists diff empty, with and without the change. The +14 passes are this port's tests. On
pandas 2.3.3 the two failures are `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
(the known break in CLAUDE.md) and `test_wilder_rma.py::test_the_incumbents_did_not_move`
(recorded in `RangeCompressRunMeasured.md`). The 42 pandas-3 failures predate this port and were
not triaged. The suite is **not green on either venv**, and the Backtesting suite was not run.

## Dictionary row provenance

`docs/IndicatorDictionary.md` was hand-patched, as the header there explains. The row was copied
verbatim from `.venv-pd2/bin/python docs/gen_indicator_dictionary.py <scratch>` (pandas 2.3.3,
no TA-Lib; the rest of that output was discarded because it empties `cdl_pattern`):

```
| `maxvol_adv` | V | `short=None`, `long=None` | `MAXVOLADV_14_50` SF | 49 | The largest single-bar volume of the last `short` bars, divided by the average volume of the last `long` bars (ADV). 1 means the peak bar was an… |
```

The same run's header counts were 239 probed, 237 in `Category`, 245 callable as `df.ta`, and
volume (25).
