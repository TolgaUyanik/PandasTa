# halflife — measured

> **Status: HLIFE-1 and HLIFE-2 (Gates A, B, D) pass; Gate C's real-data counts, HLIFE-3 (Gate E)
> and HLIFE-4 are owed (issue [#4](https://github.com/TolgaUyanik/PandasTa/issues/4)).**
> Gate E and Gate C's real-data counts need the private Backtesting engine and the BIST cache,
> which the author's machine does not have. Until a Gate E run is recorded in
> `docs/gate_e_ledger.csv`, `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
> owes a row for `halflife`: a **skip** in CI (`ci.yml` sets `GATE_E_PENDING_OK=1` on PRs into
> `dev`), a failure without that variable. `mtd_ret` (#206) is owed on `dev` the same way (see
> Gate F). Merging is the owner's call.
>
> **Review rounds 1 and 2 (2026-11-08/09)** changed the implementation (rolling cov/var, then
> blocked and anchored with an exact flatness test; the NaN domain) and replaced the Gate A oracle;
> every number below is from the current code. The records are
> `D:\pandas_ta_issues\docs\reviews\2026-11-08-issue-4-halflife-review.md` and
> `...\2026-11-09-issue-4-halflife-review-r2.md` (outside the repo) and the PR #256 thread.

`HLIFE_100` is the Ornstein-Uhlenbeck mean-reversion half-life in bars: over the last 100
one-bar pairs, regress `dP_t = close_t - close_{t-1}` on `P_{t-1} = close_{t-1}` with an
intercept; with slope `lambda`, `HLIFE = -ln(2) / lambda`. A half-life exists only for
`-1 < lambda < 0`; outside it the column is NaN. Module `pandas_ta/statistics/halflife.py`, tests
`tests/test_halflife.py`, branch `issue-4-hlife`.

## Source and decisions

The formula is the one issue #4 specifies (HLIFE-1): *"Regress `dP_t` on `P_{t-1}` over a rolling
window; with slope `lambda`, half-life `= -ln(2)/lambda` in bars."* The issue cites it as the
standard O-U half-life of the stat-arb literature (Chan), via NotebookLM syntheses it treats as a
source of a formula only. Gate A therefore does not rest on a transcription: it uses the issue's
own oracle, synthetic O-U processes with a known `theta`.

* **NaN outside `-1 < lambda < 0`** (the decision HLIFE-1 says must be made explicitly). Taken by
  this port's author, not by the owner: **the owner should confirm it or pick a clipped ceiling or
  a signed value instead.**
  * `lambda >= 0` (trending, random-walk-like): a negative or infinite half-life would put
    "trending" on the same axis as "reverts fast", and an `inf` poisons tree splits.
  * `lambda <= -1` (added in review round 1; **its own decision for the owner**): this is outside
    monotone decay, but not all of it is non-reverting. At `lambda = -1` the deviation vanishes in
    one bar. For `-2 < lambda < -1` it flips sign each bar but still decays (a damped oscillation,
    still mean-reverting). Only `lambda <= -2` fails to decay. Before review round 1 such windows
    read `-ln(2)/lambda`, e.g. 0.347 "bars" for the alternating 10/12 fixture (`lambda = -2`).
    **Cost of cutting at −1:** the fastest reverters share NaN with trending windows. On one
    20,000-bar O-U path per theta (seed 7), the share of post-warm-up bars that are NaN:

    | theta | 0.8 | 0.9 | 1.0 | 1.2 | 1.5 | 2.0 |
    |---|---|---|---|---|---|---|
    | NaN, cut at −1 (current) | 3.7% | 20.8% | 55.9% | 98.5% | 100% | 100% |
    | NaN, cut at −2 (alternative) | 0% | 0% | 0% | 0% | 0% | 47.1% |

    Alternatives: keep −1 with this caveat, or NaN only for `lambda <= -2`.
  * A flat window (no variance in `P_{t-1}`) is NaN too, tested exactly (rolling max == min of
    `P_{t-1}`), not by `var > 0`: pandas 3 can leave a ~1e-12 residue in a flat window's rolling
    var. In review round 2 that produced half-lives of 68 to 105,244 bars on 43 of 200
    flat-then-move series on pandas 3.0.0 (0 on 2.3.3). Pinned by `test_flat_then_move_is_nan`.
  * Pinned by `test_no_half_life_outside_minus_one_to_zero_is_nan`.
* **`-ln(2)/lambda`, not `-ln(2)/ln(1 + lambda)`**, kept deliberately as the issue states it; the
  Gate A oracle compares like with like (`ln(2)/theta`). The exact AR(1) half-life is shorter, and
  not negligibly so in the fast regime: by 2.5% at `lambda = -0.05` (13.51 vs 13.86 bars), 10.4% at
  `-0.2` (3.11 vs 3.47) and 27.9% at `-0.5` (1.00 vs 1.39).
* **Raw close, not log close.** The issue regresses the price level. `lambda` is a ratio of sums
  that each scale by `k²` under `close × k`, so the column is scale-free without a log.
  Power-of-two scaling is exact in floating point, in any summation order, so ×8/×64 are
  bit-identical (Gate D).
* **Default `length = 100`.** The issue does not fix a window. 100 matches the persistence family
  already shipped (`kpss`, `cusum`) and #85's `lean_hurst_100`. It is a choice, and the bias below
  is the main argument for revisiting it.
* **Rolling sums, as HLIFE-1 asks, in independent blocks.**
  `lambda = rolling cov(dP, P_{t-1}) / rolling var(P_{t-1})` (pandas), O(n) time and memory.
  Review round 1 replaced a `sliding_window_view` version that was O(n·length), the cost the
  issue names.
  * **Path dependence, and its bound.** pandas' online add/remove keeps the rounding of every value
    that has left the window, so an unblocked column depends numerically on the whole history, by
    an amount that grows with the size of the departed values. Measured against the centred
    per-window computation: round 1's unblocked code was 5.5% off after a level collapse from 1e5 to
    1 (the reviewer saw 15% on another recipe, 6.8e-6 after a single 1e7 bad tick).
  * **The fix (round 2).** Each block of `4 · length` output bars is computed on its own slice,
    starting `length` closes early, with the slice's first close subtracted (shift-invariant,
    smaller sums). A residue therefore ends at the next block boundary, and from there the output
    is bit-identical to a run that never saw the departed values.
  * **Measured on the current code vs the centred computation:**

    | input | max relative difference |
    |---|---|
    | collapse 1e5 → 1 | 7.8e-14 |
    | walk near 100, 20k bars, seed 0 | 5.5e-13 |
    | walk near 1e4, σ 0.01%, 100k bars | 1.5e-12 |
    | 1e4 + N(0, 0.01) | 7.9e-15 |
    | 1e8 + N(0, 1e-3) | 3.7e-9 |
    | 1e7 bad tick, inside its block | 2.1e-5 |
    | 1e7 bad tick, from the next block on | 3.0e-14 |

    All are identical on pandas 2.3.3 and 3.0.0.
  * **Timing.** Length 2,000 on 20,000 bars: 0.009 s (centred: 0.87 s). Length 100 on 100,000
    bars: 0.4 s.

## ⚠ What the default window can and cannot see

Measured in `tests/test_halflife.py`, and the most important thing to know before reading this
column:

| process | true `ln(2)/theta` | median, 100-bar windows (one 20,000-bar path, seed 7) |
|---|---|---|
| O-U theta 0.02 | 34.66 | 12.35 (−64%) |
| O-U theta 0.05 | 13.86 | 8.83 (−36%) |
| O-U theta 0.10 | 6.93 | 5.58 (−20%) |
| O-U theta 0.20 | 3.47 | 3.12 (−10%) |

At 100 bars the OLS AR(1) slope is biased negative (the Kendall/Hurwicz small-sample bias; at a
unit root, the Dickey-Fuller distribution), so **a random walk almost always reads as
mean-reverting**. Over 200 independent 101-bar random walks (σ = 1%), only 8 of 200 last bars are
NaN; the readings have median 14.87 bars, 10th percentile 6.0 and 90th percentile 52.5. Readings in
that range cannot be told apart from no reversion, and a slow reverter (true 34.7) reads like a
random walk. Fast reversion does separate: 200 O-U(0.2) windows read median 3.06, and all 200 are
below the random-walk median. On the seed-11 tick-rounded walk, 5 of the 1,100 post-warm-up bars
are NaN.

So the NaN branch fires rarely on prices that look like random walks. The issue expected
"`lambda >= 0` on a trending or random-walk window", and that is true of the population `lambda`,
not of its 100-bar estimate. Whether the column still carries information on BIST is what Gate E
measures. A longer window cuts the bias at the cost of responsiveness: at 2,000 bars the median
error over K = 50 paths is −1.6% … +0.8% (standard error of the median 3.6% at theta 0.02), so no
bias is detectable at that resolution. That is the owner's call if Gate E disappoints.

## Gates

Environment for Gates A, B and D: the author's machine, Windows, Python 3.13.14. Two venvs:
`.venv-pd2` with pandas 2.3.3, numpy 2.5.4 and TA-Lib 0.7.1, and `.venv` with pandas 3.0.0 and
numpy 2.4.2. `tests/test_halflife.py` passes in both: 32 of 32.

| Gate | Result |
|---|---|
| A (HLIFE-1) | **(a) Known-truth oracle:** for each theta, K = 50 independent 2,001-bar O-U paths (seeds 1000–1049), one 2,000-pair estimate per path. Median relative error against `ln(2)/theta`: −1.56%, +0.83%, +0.09%, +0.60% at theta 0.02, 0.05, 0.1, 0.2. A single path is noisy: SD 20.3%, 13.3%, 9.0%, 6.3% (min/max −35%/+47% at theta 0.02), so the standard error of the median (1.2533·SD/√K) is 3.6%, 2.3%, 1.6%, 1.1%. Asserted: \|median error\| ≤ 3 such standard errors, with the SDs fixed at their measured values rather than recomputed from the sample, plus the sample SD within ±25% of them (a variance blow-up fails instead of widening its own band). **(b) Hand fixture:** closes 10, 12, 13, 13.5 at length 3 → `lambda = -0.5` → 2·ln 2 = 1.3863, arithmetic in the test. **Independent loop:** `np.polyfit` per window, on a walk and an O-U path at lengths 100, 30 and 3: max relative difference 2.1e-12, NaN masks identical (asserted rtol 1e-8). **Hostile inputs** (table in "Rolling sums" above): a 1e5 → 1 collapse and a 1e7 bad tick are pinned against the same loop, by `test_hostile_inputs_stay_precise`. **Bias at the default window:** pinned (table above). **NaN branch:** an accelerating trend, a flat series, alternating 10/12 (`lambda = -2`) and an explosive zig-zag are NaN throughout; no value is ≤ 0 or inf. |
| B (HLIFE-2) | Future perturbation at 31 offsets, with two futures (another walk, and the same walk ×1000). The real module leaks at 0 of 31. Two one-bar look-ahead mutants (`importlib` source read, `exec`'d in memory) are each shown to change the output, then caught at 31 of 31: the slope written one bar early (`.shift(-1)`), and the one-bar change read one bar ahead. **No recursive stage, measured on values:** a +5% move of close 500 changes all 101 bars whose window holds it (each by at least 7.2%), leaves every bar before 500 bit-identical, moves bars 601–799 by at most 6.6e-15 relative, and leaves every bar from 800 (the next block) bit-identical. The 601–799 residue is a numerical dependence on a departed value, the rounding of pandas' rolling add/remove, bounded by the block. An EMA-smoothed mutant moves later bars by 0.25 and is caught by the same test. |
| C (HLIFE-2) | **Owed** (real BIST counts come from the Gate E run). Synthetic, seed-11 walk: 1,095 non-NaN of 1,100 post-warm-up bars, 1,095 distinct values, range 3.13 to 2,341 bars. The NaN branch fires on 5 of 1,100 bars here, so it is reachable and not always on. |
| D (HLIFE-2) | Close ×8 and ×64 are bit-identical. ×10 and ×3.7 differ by at most 1.1e-13 and 9.5e-14 relative; the test asserts ≤ 1e-10, because relative error grows as `lambda` nears 0 (values up to 2,341 bars). NaN masks match in all four. |
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
real-data measurement, pinned by `test_family_overlap_on_synthetic_walks`: on 10 tick-rounded
3,000-bar walks (`_walk(3000, seed)`, σ = 1.5%, seeds 0–9), signed Spearman ρ on pairwise-complete
bars of `HLIFE_100` against `KPSS_100` has median 0.240 (max 0.458), against `CUSUM_100` median
0.224 (max 0.334), and against `ZSCORE_20` median −0.008. The real-data ρ against `KPSS_100` and
`CUSUM_100` on the 89 frames is owed with HLIFE-3. #85 (`lean_hurst_100`), `variance_ratio` and a
rolling ADF stay blocked until HLIFE-3 reports, as #4 says.

### Gate F (the author's machine, `.venv-pd2`)

Run with CI's two `--deselect`s. `dev` moved while this PR was open; the branch merged
`origin/dev` at `830cb97` (2026-11-09; conflicts only in the shared counters and one `core.py`
accessor block). With `GATE_E_PENDING_OK=1`, as CI runs:

| tree | result |
|---|---|
| `dev` at `830cb97` | 0 failed, 4778 passed, 84 skipped |
| this branch (merge `f0b208d`) | 0 failed, **4811 passed**, 84 skipped |

The +33 passes are the 32 tests of `tests/test_halflife.py` and
`test_every_new_indicator_has_gate_b_and_d_tests[halflife]`; the extra skip in both is the owed
ledger row (`mtd_ret`, #206, on `dev`; `halflife` here), which fails instead without the
variable. Earlier, on the `12891bd` base (2026-11-08/09): `dev` 4437 passed / 84 skipped, this
branch 4470 / 84; without the variable 1 failed in each (`mtd_ret`; `['halflife', 'mtd_ret']`).
CI runs: `7c4896e` 4463 passed / 86 skipped, `835eba1` (run 42519643902) 4466 passed / 86
skipped, both green on numpy 1.26.4 without statsmodels. CI prints no skip reasons; its 2 passes fewer and 2 skips more than the local run are
consistent with `kpss`'s two statsmodels oracle tests, which `importorskip`, and CI does not
install statsmodels. That is an inference, not a measurement.

## Dictionary row provenance

`docs/IndicatorDictionary.md` was **fully regenerated** with
`.venv-pd2/Scripts/python docs/gen_indicator_dictionary.py` (pandas 2.3.3, numpy 2.5.4, TA-Lib
0.7.1). On 2026-11-08 a same-day run on `dev` (`12891bd`) without this port reproduced the
committed file exactly (the generator stamps the probe date, so a run on another day differs in
that line). After merging `dev` at `830cb97` it was regenerated again (2026-11-09). The diff
against `origin/dev`, enumerated line by line: the `halflife` row (`HLIFE_100` SF, warm-up 100),
`statistics (29)`, the counts (300 probed, 298 in `Category`, 306 callable), and `halflife` added
to the *Feed-ready shortlist*. Nothing else. The row's description is cut at 150 characters,
before any docstring text the review rounds changed.

README: 298 in `Category`, 306 callable, `statistics (29)`. `docs/MLCompanionContract.md` follows
the dictionary: 643 tagged columns, 286 `SF`.

HLIFE-4 is owed: `docs/indicators/halflife.md` was not generated (`docs/gen_indicator_pages.py`
reads Gate E runs from `../Backtesting`, absent here), and the parent's
`gen_indicator_register.py` / `family_index.yaml` pickup is the owner's side.
