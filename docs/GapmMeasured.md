# Gap Momentum — measured (`gapm`)

**Status: BUILT 2026-10-28 (issue #189, B2-GAPM-40). Gates A, B and D cleared; C is synthetic
only; F is clean against the baseline on both venvs, but the baseline is not green. Owed on the
Backtesting machine: E, real-data C (fire counts), and the real-data NaN rate (stop and ask the
owner if it is material).
The step-1 equivalence check split by frame, and the owner ruled PORT on 2026-10-28 (next
section).** Gate E on the real BIST frames decides: if it strikes, revert and keep this file as
the receipt.

Column `GAPM_40_20`: an EMA (span 20) of the sum of up gaps over the sum of down gaps across
40 bars, where a gap is `open - close[1]`. Category `momentum`. Above 1 means up gaps have
outweighed down gaps. Gaps are in price units, and the units cancel in the ratio.

## Source

* Perry J. Kaufman, "Gap Momentum", TASC, January 2024. This citation is **from recollection**.
  The article was not checked.
* Reddit, r/algotrading post 1brndbe (2024-03-30), https://www.reddit.com/r/algotrading/comments/1brndbe/.
  Tier 4 crowd talk. The post says: "Measures the ratio of cumulative upward price gaps to
  downward price gaps over a specified period." The poster also claims a predictive trend signal
  that works better in uptrends (tested on QQQ). **None of that is tested here.**

The following are this fork's choices (the owner's answers of 2026-10-28), not the source's:
* the EMA smoothing;
* the lengths 40 / 20 (the thread gives none);
* a NaN ratio, never inf, when the window holds no down gap. Kaufman's "ratio = 1" rule is not
  used.

The screen prototype (`docs/issues/screen/ind_screen_r8.py`) and the BIST frames are not on this
machine, so there was **no prototype cross-check**, and every number below is **synthetic only**.

## Step 1 — equivalence against the shipped package (split; owner ruled PORT)

Method: GAPM was computed inline from the owner's formula. It was compared with every
`Category` column that was scale-free at defaults: equal under price ×8 within 1e-6 relative,
NaN masks matching, and at least 2 distinct values. The statistic is pooled Spearman ρ over six
2,000-bar frames, seeds 1–3, each raw and tick-rounded to 0.01. Scripts:
`equiv.py` / `equiv_overnight.py` in the session scratchpad (not committed).

| frames | comparators | top \|ρ\| (n) | verdict by the table |
|---|---|---|---|
| `make_df` (the generator's frame) | 328 | 0.9054 `trixh:TRIXs_18_9` (11,646); 0.8883 `trix:TRIX_30_9`; 0.8773 `trixh:TRIX_18_9`; 0.8642 `ichimoku_ml:ICHI_CHIKOU_VS_CLOUD`; 0.8508 `trix:TRIXs_30_9` | **EQUIVALENT** (≥ 0.90) |
| overnight/intraday walk | 333 + `gapm` itself | 0.3258 `trix:TRIX_30_9` (11,646); 0.3203 `ICHI_CHIKOU_VS_CLOUD`; 0.3199 `TRIXs_18_9`; 0.3176 `TRIXs_30_9`; 0.3101 `HALFTREND_DIR` | **PORT** (< 0.80) |
| issue's stage 2, 12 real frames | scale-free `Category` outputs | 0.4526 `trix:TRIX_30_9` | from the issue #189 body, measured on prototype `ind_screen_r8` and not re-run. The prototype's formula was not cross-checked, so this says nothing certain about `GAPM_40_20` |

Why the two disagree: `make_df` builds `open_t = close_t × (1 + N(0, 0.004))`. Its gap,
`open_t − close_{t−1}`, is therefore mostly the bar's own close-to-close move, so a ratio of up gaps
to down gaps becomes a smoothed up/down return ratio, which is what TRIX also measures. The
overnight walk builds `open_t = close_{t−1} × exp(overnight)` and `close_t = open_t × exp(intraday)`,
with sd 0.004 and 0.011. On that frame the gap carries only the overnight part. The issue's
stage-2 check on 12 real frames measured max |ρ| 0.4526 against `trix:TRIX_30_9`, which is
consistent with the second row, not the first. On the overnight frame, the port's
`df.ta.gapm()` (run as part of the `Category` sweep) matched the inline formula with ρ 1.0000.

**Owner's decision, 2026-10-28: PORT.** The split was reported to the owner with the numbers
above. The owner ruled PORT, with Gate E on the real BIST frames as the measurement that decides. No `docs/EquivalentStrategies.md` row was written. If
Gate E strikes, revert the port and keep this file as the receipt.

## The zero-denominator rule (NaN rate)

A window with no down gap gives a NaN ratio. The EMA skips that ratio (`ignore_na=True`: it is
neither a sample nor a decay step), and the output on that bar is set to NaN instead of carrying
the last value. The EMA emits only after `signal` valid ratios, so the first value is at bar 59.

| frame | windows with no down gap |
|---|---|
| `make_df`, seeds 0–4, 560 windows each, raw | 0 |
| same, tick-rounded to 0.01 (1–3 exact-zero gaps per frame) | 0 |
| tick walk, open == prior close forced on p of bars, 5 seeds × 1,960 windows: p = 0 / 0.3 / 0.5 | 0 / 0 / 0 |
| same: p = 0.7 / 0.8 / 0.9 | 31 (0.32%) / 330 (3.37%) / 1,477 (15.07%) |
| test walk (seed 11, 2,000 bars, 1,960 full windows): p = 0.5 / 0.7 / 0.8 / 0.9 | 0 / 2 (0.10%) / 50 (2.55%) / 399 (20.36%) |

The rate is 0 until roughly 70% of bars open exactly at the prior close. Above that it becomes
material. **It was not measured on real data.** If BIST frames open at the prior close on most
bars, the NaN rate needs re-measuring there before ship; that is not known here. 
### The tail is lopsided

The ratio is floored at 0 and unbounded above, so the column is not symmetric around 1. GAPM on
the 2,000-bar seed-11 test walk (measured on both venvs, identical):

| p (open == prior close) | min | median | max |
|---|---|---|---|
| 0 | 0.447 | 1.042 | 2.447 |
| 0.8 | 0.176 | 1.254 | 26.385 |
| 0.9 | 0.003 | 1.396 | 30.643 |

A tree is invariant to monotone transforms, so this matters less there than for a linear model.
If real-data Gate C shows heavy tails, the owner has two options: `log(ratio)`, or
`up / (up + dn)`, which is bounded in [0, 1]. Either is a formula change, and neither was made.

A draft also
guarded against float residue in the rolling sum. The "residue" it found was the NaN sum at bar
39 (`NaN != 0`), not residue, so the guard was dropped.

## Follow-up (not done here)

* `docs/MLCompanionContract.md` quoted 568 tagged columns / 49 `ORD`, but the dictionary's Counter
  says 570 / 50. This port corrected the sentence. The guard,
  `test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`, checks
  only `PX`/`SF`/`BIN`/`PX2`, which is how the `ORD` and total drift got through. Extending it is
  that module's change and was left alone.

## Departures from the instructions

* **Dictionary hand-patched.** Neither venv has TA-Lib. Without it, a full run of
  `python docs/gen_indicator_dictionary.py` strips the `cdl_pattern` row from 62 columns to 2,
  and other rows drift too (30 changed lines on `.venv-pd2`, 72 on `.venv`). So, as was done for
  `pfe`, `kalman_trend`, `range_compress_run` and `dpo`, the `gapm` row, its scale-free list entry
  and the counts were copied verbatim from a `.venv-pd2` run and patched in by hand. The
  dictionary header says so.
* **`fill_method` uses `ffill()` / `bfill()`**, not the neighbours' `fillna(method=...)`. That call
  is gone in pandas 3 (the baseline `test_bpress::test_fill_method_kwarg` fails on it).
  `'ffill'`/`'pad'` forward-fill; any other value back-fills.

## Gates

Synthetic numbers come from `tests/test_gapm.py`. The frame there is a 1,200-bar tick walk
(0.01 tick, seed 11), with open = prior close × overnight move and close = open × intraday move.

| Gate | Result |
|---|---|
| A | Checked line by line against the owner's formula: `gap = open − close[1]` → `up/dn = clip` → `SUM(·, 40)` ratio → NaN when the down sum is not > 0 → EMA. An independent Python loop (sums, ratio, the EMA recursion with NaNs skipped, and `signal` valid ratios before the first output) matches within rtol 1e-12 with identical NaN masks, at p = 0 and at p = 0.8. Also checked: a hand-computed 6-bar sequence, a hand-computed no-down-gap sequence, a NaN input (blanks exactly the 40 windows it sits in), `offset`, `fillna`, `fill_method`. |
| B | Future perturbation at 31 offsets: the real module leaks at 0. Two look-ahead mutants, `close.shift(-1)` in the gap and `up.shift(-1)` in the up-gap sum, are each proved live and caught at 31 of 31. With the random future alone, the `window` mutant was caught at only 28 of 31, so a second future (every open 1000 above the prior close) was added. |
| C | Synthetic only: 706 bars above 1, 435 below, 59 NaN (warm-up), 1,141 distinct values in 1,200 bars. **Not measured on real data**, because the BIST frames are not on this machine. |
| D | ×8 and ×64 bit-identical; ×10 and ×3.7 within a relative 1.73e-14 / 1.36e-14, the same on `.venv-pd2` and `.venv` (pinned at 1.8e-14); all four with matching NaN masks; `0 < (GAPM > 1) < n`. |
| E | **Owed.** The only numbers are from the issue #189 body, measured on prototype `ind_screen_r8` and not re-run: max \|ρ\| 0.3746 vs `ZIGZAG`, n = 33,418; top-5 per-frame median 0.5052. The prototype's formula was not cross-checked, so these say nothing certain about `GAPM_40_20`; they would be SHIP only if the two formulas match. To re-run, from `../Backtesting/Backtesting`: `python scripts/analysis/gate_e_overlap.py run --module pandas_ta.momentum.gapm --name gapm`. |
| F | See below. The Backtesting suite was not run, because that repo is not on this machine. |

### Gate F, this repo (measured 2026-10-28, base `dev` at `d7fd91d`)

| venv | clean `d7fd91d` | with this change |
|---|---|---|
| `.venv-pd2` (pandas 2.3.3) | 2 failed, 3187 passed, 86 skipped | 2 failed, 3201 passed, 86 skipped |
| `.venv` (pandas 3.0.6) | 42 failed, 3147 passed, 86 skipped | 42 failed, 3161 passed, 86 skipped |

In both venvs the failing tests are the same with and without the change. The +14 passes are
`tests/test_gapm.py`. On `.venv-pd2` the two failures are
`test_pine_coverage_csv::test_audited_rows_carry_their_evidence` and
`test_wilder_rma::test_the_incumbents_did_not_move`, so the full `df.ta.strategy()` sweep tests
pass there with `gapm` registered.

Strategy path, both venvs, on a 600-bar overnight walk: `ta.gapm(open, close)` gives
`GAPM_40_20` with 541 valid bars. `df.ta.gapm()` is equal to it. A `ta.Strategy` holding only
`gapm` (defaults plus `length=10, signal=5`) appends `GAPM_40_20` and `GAPM_10_5`, and the first is
equal to the direct call. `df.ta.strategy("momentum")` appends a `GAPM_40_20` equal to the direct
call.
