# halflife — measured

> **Status: HLIFE-1 and HLIFE-2 (Gates A, B, D) pass; Gate C's real-data counts, HLIFE-3 (Gate E)
> and HLIFE-4 are owed (issue [#4](https://github.com/TolgaUyanik/PandasTa/issues/4)).**
> Gate E and Gate C's real-data counts need the private Backtesting engine and the BIST cache,
> which the author's machine does not have. Until a Gate E run is recorded in
> `docs/gate_e_ledger.csv`, `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
> fails on this branch. On `dev` it already fails for `mtd_ret` (#206); this branch adds
> `halflife` to the same message (see Gate F). Merging is the owner's call.

`HLIFE_100` is the Ornstein-Uhlenbeck mean-reversion half-life in bars: over the last 100
one-bar pairs, regress `dP_t = close_t - close_{t-1}` on `P_{t-1} = close_{t-1}` with an
intercept; with slope `lambda`, `HLIFE = -ln(2) / lambda`. Where `lambda >= 0` there is no
half-life and the column is NaN. Module `pandas_ta/statistics/halflife.py`, tests
`tests/test_halflife.py`, branch `issue-4-hlife`.

## Source and decisions

The formula is the one issue #4 specifies (HLIFE-1): *"Regress `dP_t` on `P_{t-1}` over a rolling
window; with slope `lambda`, half-life `= -ln(2)/lambda` in bars."* The issue cites it as the
standard O-U half-life of the stat-arb literature (Chan), via NotebookLM syntheses it treats as a
source of a formula only. Gate A therefore does not rest on a transcription: it uses the issue's
own oracle, synthetic O-U processes with a known `theta`.

* **`lambda >= 0` → NaN** (the decision HLIFE-1 says must be made explicitly). Taken by this
  port's author, not by the owner: **the owner should confirm it or pick a clipped ceiling or a
  signed value instead.** A negative or infinite half-life would put "trending"
  on the same axis as "reverts fast", and an `inf` poisons tree splits. A flat window (no variance
  in `P_{t-1}`) is NaN too. Pinned by `test_not_mean_reverting_is_nan_never_negative_or_inf`.
* **`-ln(2)/lambda`, not `-ln(2)/ln(1 + lambda)`.** The issue's form is the continuous-time
  approximation. The exact AR(1) half-life is shorter: by 2.5% at `lambda = -0.05` (13.51 vs
  13.86 bars), and by less as `lambda` approaches 0.
* **Raw close, not log close.** The issue regresses the price level. `lambda` is a ratio of sums
  that each scale by `k²` under `close × k`, so the column is scale-free without a log, and with
  centred sums it is bit-identical under ×8/×64 (Gate D).
* **Default `length = 100`.** The issue does not fix a window. 100 matches the persistence family
  already shipped (`kpss`, `cusum`) and #85's `lean_hurst_100`. It is a choice, and the bias below
  is the main argument for revisiting it.
* **Vectorised.** HLIFE-1 asks for rolling sums instead of a per-bar `polyfit`. The port uses
  `sliding_window_view` with centred sums per window, which is vectorised as asked and avoids the
  cancellation of raw rolling sums (`Σx² - (Σx)²/n` loses digits when the price level is large
against its range in the window). Memory
  is O(n·length): about 8·n·length bytes per intermediate array, 16 MB at n = 20,000.

## ⚠ What the default window can and cannot see

Measured in `tests/test_halflife.py`, and the most important thing to know before reading this
column:

| process (20,000 bars, seed 7) | true `ln(2)/theta` | median, 2,000-bar windows | median, 100-bar windows |
|---|---|---|---|
| O-U theta 0.02 | 34.66 | 34.99 (+0.95%) | 12.35 (−64%) |
| O-U theta 0.05 | 13.86 | 14.13 (+1.92%) | 8.83 (−36%) |
| O-U theta 0.10 | 6.93 | 7.04 (+1.58%) | 5.58 (−20%) |
| O-U theta 0.20 | 3.47 | 3.49 (+0.62%) | 3.12 (−10%) |

At 100 bars OLS pulls `lambda` negative (the Dickey-Fuller small-sample bias), so **a random walk
almost always reads as mean-reverting**. Over 200 independent 101-bar random walks (σ = 1%), only
8 of 200 last bars are NaN, and the median is 14.87 bars. A slow reverter (true 34.7) and a random
walk read about the same. Fast reversion does separate: 200 O-U(0.2) windows read median 3.06, and
all 200 are below the random-walk median. On the seed-11 tick-rounded walk, 5 of the 1,100
post-warm-up bars are NaN.

So the NaN branch fires rarely on prices that look like random walks. The issue expected
"`lambda >= 0` on a trending or random-walk window", and that is true of the population `lambda`,
not of its 100-bar estimate. Read the column as "how fast this window reverts, read through a
noisy short-window estimator whose floor for a random walk is about 15 bars". Whether that still
carries information on BIST is what Gate E measures. A longer window cuts the bias (2,000 bars:
within 2%) at the cost of responsiveness; that is the owner's call if Gate E disappoints.

## Gates

Environment for Gates A, B and D: the author's machine, Windows, Python 3.13.14. Two venvs:
`.venv-pd2` with pandas 2.3.3, numpy 2.5.4 and TA-Lib 0.7.1, and `.venv` with pandas 3.0.0 and
numpy 2.4.2. `tests/test_halflife.py` passes in both: 27 of 27.

| Gate | Result |
|---|---|
| A (HLIFE-1) | **(a) Known-truth oracle:** the median over all 2,000-bar windows of 20,000-bar O-U processes recovers `ln(2)/theta` to +0.95%, +1.92%, +1.58%, +0.62% at theta 0.02, 0.05, 0.1, 0.2, asserted within 3% (the stated tolerance). **(b) Hand fixture:** closes 10, 12, 11, 11.5 at length 3 → `lambda = -1.5` → `ln(2)/1.5` = 0.4621, arithmetic in the test. **Independent loop:** `np.polyfit` per window, on a walk and an O-U path at lengths 100, 30 and 3: max relative difference 2.1e-12, NaN masks identical (rtol 1e-9). **Bias at the default window:** pinned (table above). **Non-mean-reverting branch:** an accelerating trend and a flat series are NaN throughout; no value is ≤ 0 or inf. |
| B (HLIFE-2) | Future perturbation at 31 offsets, with two futures (another walk, and the same walk ×1000). The real module leaks at 0 of 31. Two one-bar look-ahead mutants (`importlib` source read, `exec`'d in memory) are each shown to change the output, then caught at 31 of 31: the output written one bar early (`values[length - 1:-1]`), and the window read one bar ahead. **No recursive stage**, measured as such: a NaN close blanks exactly its own bar and the next 100, and every later bar's NaN mask equals the unperturbed one, so the taint reach is the `length + 1`-close window. |
| C (HLIFE-2) | **Owed** (real BIST counts come from the Gate E run). Synthetic, seed-11 walk: 1,095 non-NaN of 1,100 post-warm-up bars, 1,095 distinct values, range 3.13 to 2,341 bars. The issue's `0 < fires < n` applies to the NaN branch: it fires on 5 of 1,100 bars here, so it is reachable and not always on. |
| D (HLIFE-2) | Close ×8 and ×64 are bit-identical. ×10 and ×3.7 differ by at most 1.2e-13 and 1.0e-13 relative; the test asserts ≤ 1e-11, because relative error grows as `lambda` nears 0 (values up to 2,341 bars). NaN masks match in all four. |
| E (HLIFE-3) | **Owed.** Pre-registered below. From `../Backtesting/Backtesting`, with `issue-4-hlife` checked out as the PandasTa sibling (`record` checks the run's `pandas_ta_src_sha1` against this tree): `python scripts/analysis/gate_e_overlap.py run --module pandas_ta.statistics.halflife --name <run name>`, then `python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD`. |
| F | **No new regressions in this repo** (below). Backtesting not run. |

### HLIFE-3 pre-registration (written before any Gate E number exists)

* **Ladder** (`r3-perframe-0.90`, as issue #4 states it): STRUCK if pooled |ρ| ≥ 0.90 or a top-5
  comparator's per-frame median ≥ 0.90 → revert (HLIFE-4: delete the module, keep this file, add it
  to the reverted list). DISCLOSE_GAP 0.80 ≤ ρ < 0.90 and DISCLOSE 0.76 ≤ ρ < 0.80 → ship with the
  comparator named here. SHIP < 0.76 → ship.
* **Read specifically**, as the issue asks: `natr`, `natr_percentile`, `ZSCORE_20`, `BB_BWidth`
  and the `LINREG_*` family, plus the run's top-5.
* **Prediction**, not a measurement: low ρ against the engine set. Gate E is blind to the family,
  so the family check is separate (next section).
* Record the per-column ρ table with n in this file, then the verdict against this ladder.

### The family (issue #4's tie rule)

#4 says to measure the persistence family against its survivor, because Gate E only compares a
candidate with the engine's shipped columns. Since #4 was written, two family members have shipped
in this fork: `kpss` (#157) and `cusum` (#16). Per Tolga's note on #16, `kpss` is not among Gate
E's comparators, so the harness will not see this overlap. A synthetic indication, **not** the
real-data measurement: on 10 tick-rounded 3,000-bar walks (seeds 0–9), Spearman ρ of `HLIFE_100`
against `KPSS_100` has median 0.24 (max 0.46), against `CUSUM_100` median 0.22 (max 0.33), and
against `ZSCORE_20` median −0.01. The real-data ρ of `HLIFE_100` against `KPSS_100` and
`CUSUM_100` on the 89 frames is owed with HLIFE-3. #85 (`lean_hurst_100`), `variance_ratio` and a
rolling ADF stay blocked until HLIFE-3 reports, as #4 says.

### Gate F (2026-11-08, the author's machine, `.venv-pd2`)

Run with CI's two `--deselect`s:

* `dev` at `12891bd`: 1 failed, 4437 passed, 83 skipped. The failure is
  `test_every_indicator_that_needs_a_row_has_one`: no Gate E ledger row for `mtd_ret` (#206).
* this branch: 1 failed, 4465 passed, 83 skipped. The +28 passes are the 27 tests of
  `tests/test_halflife.py` and `test_every_new_indicator_has_gate_b_and_d_tests[halflife]`. The
  failure is the same test, now for `['halflife', 'mtd_ret']`.

## Dictionary row provenance

`docs/IndicatorDictionary.md` was **fully regenerated** with
`.venv-pd2/Scripts/python docs/gen_indicator_dictionary.py` (pandas 2.3.3, numpy 2.5.4, TA-Lib
0.7.1). The same run on `dev` without this port reproduces the committed file exactly. The diff
against `dev`, enumerated line by line on 2026-11-08: the `halflife` row (`HLIFE_100` SF, warm-up
100), `statistics (24)`, the counts (287 probed, 285 in `Category`, 293 callable), and `halflife`
added to the *Feed-ready shortlist*. Nothing else.

README: 285 in `Category`, 293 callable, `statistics (24)`. `docs/MLCompanionContract.md` follows
the dictionary: 630 tagged columns, 273 `SF`.

HLIFE-4 is owed: `docs/indicators/halflife.md` was not generated (`docs/gen_indicator_pages.py`
reads Gate E runs from `../Backtesting`, absent here), and the parent's
`gen_indicator_register.py` / `family_index.yaml` pickup is the owner's side.
