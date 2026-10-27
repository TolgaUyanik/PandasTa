# Range Compression Run — measured (`range_compress_run`)

**Status: BUILT 2026-10-26. Gates A, B and D cleared; C is partial; E is owed; F is not met (see below).**
If Gate E strikes it, revert and keep this file as the receipt.

Column `RCR_100`: the number of consecutive bars, ending at this one, whose high-low range is
strictly below the previous bar's range, clipped at `cap` (default 100). It is 0 on a bar that did
not compress and NaN on bar 0. Category `volatility`.

## Source

Reddit, r/Daytrading post 1tv21c0 (2026-06-02),
https://www.reddit.com/r/Daytrading/comments/1tv21c0/. Tier 4 crowd talk. The post names a
feature `count_consolidating_days (range compression)`. It claims this was the 5th most
predictive feature in the poster's XGBoost model, and that "Grade A" setups needed 9 consecutive
compressing days. **None of that is tested here.** The post gives no formula. The definition used
here ("today's range below the prior bar's") is the one from the 2026-10-26 screen prototype
(`b2_range_compress_run` in `docs/issues/screen/ind_screen_r8.py`). That file is not on this
machine and was not read. The 9-day claim can be read off this column as `RCR_100 >= 9`.

## Prior art in the fork

No registered indicator computed this. Two existing functions come close:

* `ml_bars_since(~compressed)` (`pandas_ta/ml/companions.py`) gives the same numbers. The port
  calls it instead of adding another copy.
* `decreasing(high - low, length=k + 1, strict=True)` gives only the yes/no flag `run >= k`, and it
  uses a plain `>` with no tie tolerance. On the seed-11 test walk (1,200 bars) it disagrees with
  `RCR_100 >= k` on 4 / 2 / 2 / 1 bars at k = 1 / 2 / 3 / 4, out of 600 / 203 / 53 / 9 bars where
  the run is that long. Every disagreement is a float tie (next section). This was measured with
  an ad-hoc probe on 2026-10-26 and is not pinned by a test.

## The tie tolerance (found during the port)

The prototype compares `range < range[1]`. Exact decimal ties are common on tick-rounded prices,
and in float a tie can come out unequal. Bars 170 and 171 of the seed-11 walk are both 57 ticks,
but `115.80000000000001 - 112.95 = 2.8500000000000085` while `117.75 - 114.9 = 2.8499999999999943`.
With the plain `<` on that walk, 4 of the 14 exact ties read as compression. Scaling prices ×10
moved 9 output bars; ×3.7 moved none.

The port compares `range < range[1] - 4 * eps * (|high| + |high[1]|)`. The rounding error of a
subtraction scales with the price, not with the range, so the tolerance does too. The first draft
used a tolerance of 1e-9 relative to the range instead, and review showed it fails once price/range
exceeds about 5e6: equal tick ranges near 1e7 read as compression. That case is pinned by
`test_tie_tolerance_holds_at_high_prices`. On the seed-11 walk, the port's flag matches integer tick
arithmetic on every bar. The tolerance is far below one tick at any realistic price.

This is a deliberate departure from the prototype, so **Gate E must be re-run on the port**: the
prototype's 0.4837 was measured with the plain `<`.

## Gates

Environment: `.venv-pd2` (pandas 2.3.3) and `.venv` (pandas 3.0.6), Python 3.12. The synthetic
numbers come from `tests/test_range_compress_run.py`: a 1,200-bar GBM walk, σ = 0.02, seed 11,
0.05 tick.

| Gate | Result |
|---|---|
| A | There is no Pine or C source, so the port was checked against the stated definition: a hand-computed 7-bar sequence (with a tie and a widening), an independent loop on integer ticks (equal on every bar), the cap, bar 0 NaN, and edge cases (a NaN mid-series blanks that bar and the next, then the run restarts; zero-width and inverted-bar ties read 0; `offset`; `fillna`). |
| B | 31-offset future perturbation, using three futures (another walk, a very wide future, a zero-width future): the real module leaks at 0 offsets. Two one-bar look-ahead mutants (`prior = rng.shift(-1)` and `rng.shift(-1) < prior - tol`) are both proved live and caught at 31 of 31. With the random rewrite alone, the `prior` mutant was caught at only 12 of 31, which is why the other two futures exist. |
| C | Synthetic only: on the seed-11 walk, 600 of 1,200 bars non-zero, 599 zero, 1 NaN; runs of 0 to 4. **Not measured on real data**, because the BIST frames are in the Backtesting repo. |
| D | On the seed-11 walk: ×8, ×64, ×10 and ×3.7 all bit-identical with matching NaN masks; `0 < fires < n`. |
| E | **Owed.** On the prototype (plain `<`, not the port): max \|ρ\| 0.4837 vs `Range_ATR_Pctl`, n = 392,352; top-5 per-frame median 0.4910 → SHIP band. To re-run, from `../Backtesting/Backtesting`: `python scripts/analysis/gate_e_overlap.py run --module pandas_ta.volatility.range_compress_run --name range_compress_run`. |
| F | **Not met.** See below. |

### Gate F, this repo (measured 2026-10-26, base `dev` at `479cd8f`)

| venv | clean `479cd8f` | with this change |
|---|---|---|
| `.venv-pd2` (pandas 2.3.3) | 2 failed, 3159 passed, 86 skipped | 2 failed, 3174 passed, 86 skipped |
| `.venv` (pandas 3.0.6) | 42 failed, 3119 passed, 86 skipped | 42 failed, 3134 passed, 86 skipped |

In both venvs the list of failing tests is identical with and without the change. The +15 passes
are this port's tests. On pandas 2.3.3 the two failures are:

* `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`, the known break listed
  in CLAUDE.md.
* `tests/test_wilder_rma.py::test_the_incumbents_did_not_move`. This one is **not** in CLAUDE.md's
  Known breaks. A frozen `natr` golden constant differs in its last digit (`2.1645906239237416` vs
  `2.164590623923742`). It already fails on clean `479cd8f`, so it predates this port, but it is
  unrecorded and unfixed.

The 42 pandas-3 failures also predate this port; they were not triaged here. The suite is therefore
**not green on either venv**, and the Backtesting suite was not run (that repo is not on this
machine). The "both repos' suites green" requirement is not met.
