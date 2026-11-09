# g191_026 — measured (issue #56)

> **Status: Gates A-D cleared, Gate E pending, run by issue-solver after this session.**

Seven-day mean gap plus 230-day VWAP/lagged-close correlation: Guotai
Junan's (2017, "GTJA191", internal quant report, read via the
HKUDS/Vibe-Trading copy, MIT) alpha `#26`, per issue #56's own instruction.
Module `pandas_ta/statistics/g191_026.py`, column `G191_026_7_230_5`. Tests:
`tests/test_g191_026.py` (16, all passing). Numbers below:
`python docs/measure_g191_026.py`. Environment: this worktree's pinned
pandas/numpy. Measured 2026-11-09.

## Gate A: derivation from the published formula, not the prototype

Issue #56 states GTJA191 alpha `#26`:

    (SUM(C,7)/7 - C) + CORR(VWAP, DELAY(C,5), 230)

with the issue's own parenthetical: "scale-free form: first term /close;
VWAP -> (H+L+C)/3".

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. Everything below is derived
from the issue's own stated formula string plus its own parenthetical
instruction, per the issue's own rule ("Gate A starts from the source
formula, not the prototype").

`SUM(C,7)/7` is a 7-bar trailing mean of close (`MEAN(C,7)`), so the raw
formula's first term is a price-unit mean-reversion gap: how far the close
sits below its own trailing 7-bar average. The issue's own conversion
divides only this term by close, leaving the already-unitless correlation
term untouched, and substitutes the typical price for VWAP:

    G191_026 = (MEAN(C, 7) - C) / C + CORR((H+L+C)/3, DELAY(C, 5), 230)

matching the issue's own prototype (`docs/issues/screen/ind_screen.py:339`):
`(mean(c, 7) - c) / c + corr(tp(h, l, c), delay(c, 5), 230)`. No disclosed
interpretation choice was needed here -- unlike `g191_165` (issue #55), this
formula's precedence and operators are unambiguous, and the issue's own
parenthetical states the conversion directly rather than leaving it to be
inferred.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula plus its own parenthetical conversion, matching the issue's own prototype line-for-line | 6-bar hand-derived example at `mean_length=3, corr_length=2, lag=1` (`tests/test_g191_026.py::test_hand_derived_six_bars`), high/low built as `close +- 1` so the typical price collapses to `close` exactly: `result[2..5] = [0.6666666666666667, 0.75, -0.606060606060606, 4.466666666666667]`, matching the module's float64 output exactly (`python docs/measure_g191_026.py`). Matches an independent per-bar loop (plain numpy `np.mean`/`np.corrcoef`, not the module's own `.rolling().mean()`/`.rolling().corr()`) at the shipped default (`mean_length=7, corr_length=230, lag=5`), 3 spot-checked bars (300, 600, 899) on a 900-bar synthetic frame, relative difference 2.9e-14 / 5.6e-15 / 2.9e-14 (float64 rounding, not a disagreement) |
| B Causality | pass | Future-perturbation sweep (OHLC series rewritten from `j` onward, another synthetic frame), 30 offsets past the 234-bar warm-up: real module **0 of 30** leaks (`python docs/measure_g191_026.py`). Two independent mutants (`importlib` source read, `exec`'d in memory), each shown live (differs from the real module) then caught at **30 of 30**: shifting the whole write index `corr_length=230` bars into the future, and flipping the backward `DELAY` (`close.shift(lag)`) into a FORWARD shift (`close.shift(-lag)`) -- turning the lag term itself into a look-ahead |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic OHLC series (seed 11, see `docs/measure_g191_026.py:_ohlc`), shipped default: **1,266 of 1,500** bars non-NaN (84.40%) -- exactly `n - 234`, the `lag + corr_length = 235`-bar warm-up (first valid index 234), no wider gap. **1,266 distinct values** observed (every fired bar distinct -- not a constant column), range `[0.508263, 0.976310]`, median `0.861435` |
| D Scale-free | pass | Pearson correlation is exactly invariant to a positive rescale of either input (the scale cancels between covariance and standard deviation), and the mean-gap term's own `/close` cancels a positive price rescale algebraically too -- so the whole column is exactly invariant algebraically for ANY `k > 0`. Measured on the 1,500-bar series: PRICE x8/x64 **bit-identical, 0.0 max\|diff\|** (power-of-two multiplication is exact in IEEE754, so the algebraic cancellation is also exact in float64); PRICE x10/x3.7: max\|diff\| **6.38e-13 / 6.91e-13** -- float64 rounding from the scalar multiply itself, well under the test's 1e-9 tolerance, not a scale dependency. `0 < 1,266 fires < 1,500` and `1,266 > 1` distinct values rule out a constant column |
| E Attribution | pending, run by issue-solver after this session | -- |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **290 -> 291** (`statistics` **24 -> 25**); `df.ta.<name>()`
accessor count **298 -> 299**. Touch points:
`pandas_ta/statistics/g191_026.py` (module),
`pandas_ta/statistics/__init__.py` (export), `pandas_ta/__init__.py` ->
`Category["statistics"]` (discovery), `pandas_ta/core.py` ->
`AnalysisIndicators.g191_026` (accessor), `tests/test_g191_026.py` (tests).
`README.md`'s headline and `statistics (25)` row, and
`docs/IndicatorDictionary.md` (regenerated), both updated and checked by
`tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s running tag
count updated **635 -> 636 / 278 -> 279 `SF`** (`G191_026_7_230_5` probes
cleanly at the dictionary's 600-bar synthetic frame and takes many distinct
values, so the generator tags it `SF`). `tests/test_altport2_ports.py`'s
`CATEGORY_TOTAL` updated to match (290 -> 291); no `CATEGORY_BUCKETS` entry
needed (that dict only tracks `trend`/`volatility`/`volume`, not
`statistics`).

The ledger row cannot be recorded yet: Gate E has not run (`docs/pine/` and
the parent `Backtesting` repo are both outside this worktree). A later
receipt session records `g191_026`'s row after the launcher's Gate E run
and fills in the Gate E line above. `mtd_ret` is also still owed in the same
assertion, pre-existing and unrelated to this port (carried over from issue
#206, per `docs/G191076Measured.md`'s identical note).

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order: **3 failed,
4608 passed, 83 skipped**. `g191_026`'s own tests (`tests/test_g191_026.py`):
**16 passed**. Pre-existing / expected failures, all unrelated to this
port's correctness (CLAUDE.md "Known breaks" plus this port's own owed Gate
E row):
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
(owed for `['g191_026', 'mtd_ret']` -- `g191_026`'s row is owed by design
per this session's override rules; `mtd_ret` pre-dates this session),
`tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this worktree)
and `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
(untracked `docs/pine/` corpus). No other test regresses.
