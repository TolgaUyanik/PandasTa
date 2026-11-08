# g191_191 — measured (issue #53)

> **Status: Gates A-D cleared, Gate E pending.** Gate E is run by the
> launcher in `../Backtesting` after this session; this file's Gate E
> section is filled in by a later receipt session once that run lands.

Volume-low correlation plus mid-to-close gap: Guotai Junan's (2017,
"GTJA191", internal quant report, read via the HKUDS/Vibe-Trading copy, MIT)
alpha `#191`, per issue #53's own instruction. Module
`pandas_ta/volume/g191_191.py`, column `G191_191_20_5`. Tests:
`tests/test_g191_191.py` (19, all passing). Numbers below:
`python docs/measure_g191_191.py`. Environment: this worktree's pinned
pandas/numpy. Measured 2026-11-09.

## Gate A: derivation from the published formula, not the prototype

Issue #53 states GTJA191 alpha `#191`:

    (CORR(MEAN(V,20), L, 5) + (H+L)/2) - C

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. Everything below is derived
from the issue's own stated formula string, per the issue's own instruction
("Gate A starts from the source formula, not the prototype").

Addition/subtraction associate freely, so the formula's grouping is cosmetic:
`(CORR(...) + (H+L)/2) - C = CORR(...) + ((H+L)/2 - C)`. `CORR(MEAN(V,20),
L, 5)` is already unitless (a Pearson correlation); `(H+L)/2 - C` is a price
difference, not scale-free. The issue's own candidate record
(`docs/issues/screen/candidates.csv`, row `g191_191`) states the conversion
applied before Gate E ever ran -- `conv = "price terms /close"` -- and the
issue's own prototype (`docs/issues/screen/ind_screen.py:584`) spells out the
identical scale-free form directly: `corr(mean(v, 20), l, 5) + ((h + l) / 2
- c) / c`. This port divides ONLY the price-difference term by `C`:

    G191_191 = CORR(MEAN(V,20), L, 5) + ((H+L)/2 - C) / C

No operator here needs a disclosed ASSUMPTION: the prototype's own module
docstring spells out `MEAN`/`CORR` unambiguously --

    def mean(x, n): return x.rolling(n).mean()
    def corr(x, y, n): return _fin(x.rolling(n).corr(y))

-- and this port reuses those spellings directly. The explicit
`min_periods=corr_length` on the correlation's rolling window is written for
readability, not for a behavior change: pandas' own `Rolling.corr` already
defaults `min_periods` to the window size for a fixed-size integer window
when unspecified, so the prototype's own un-annotated `x.rolling(n).corr(y)`
masks partial windows identically -- stated explicitly here, not measured as
different, because it is not different.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula, using the prototype's own (unambiguous) `MEAN`/`CORR` spellings -- no disclosed ASSUMPTION needed | 6-bar hand-derived example at `mean_length=3, corr_length=2` (`tests/test_g191_191.py::test_hand_derived_six_bars`), where every 2-point Pearson correlation is exactly +-1 by construction: `result[3..5] = [-1.0, 0.9791666666666652, -1.0]`, matching the module's float64 output to ~1e-9. Matches an independent per-bar loop built from plain numpy (`np.mean` over explicit slices, `np.corrcoef`, not pandas' `.rolling()`) at the shipped defaults (`mean_length=20, corr_length=5`), 3 spot-checked bars (300, 600, 899) on a 900-bar synthetic OHLCV frame |
| B Causality | pass | Future-perturbation sweep (every OHLCV series rewritten from `j` onward, another synthetic frame), 34 offsets past the 23-bar warm-up: real module **0 of 34** leaks (`python docs/measure_g191_191.py`). Two independent mutants (`importlib` source read, `exec`'d in memory), each shown live (differs from the real module) then caught at **34 of 34**: shifting the whole write index `corr_length=5` bars into the future, and computing `MEAN(volume, mean_length)` with `center=True` instead of the causal trailing window -- the same look-ahead bug class CLAUDE.md documents for `bos`'s `rolling(..., center=True)` |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic OHLCV frame (seed 11/12/23, see `docs/measure_g191_191.py:_ohlcv`), shipped defaults: **1,477 of 1,500** bars non-NaN (98.47%) -- exactly `n - 23`, the `mean_length + corr_length - 2 = 23`-bar warm-up, no wider gap. **1,477 distinct values** observed on this frame (every fired bar distinct -- not a constant column), range `[-0.992038, 0.996678]`, median `-0.007214` |
| D Scale-free | pass | Pearson correlation is exactly invariant to a positive rescale of either input (the scale cancels between covariance and standard deviation); the `/close` on the price-gap term cancels a positive price rescale algebraically too. Measured on the 1,500-bar frame: PRICE x8/x64 **bit-identical, 0.0 max\|diff\|**; VOLUME x8/x64 **bit-identical, 0.0 max\|diff\|** (power-of-two multiplication is exact in IEEE754, so the algebraic cancellation is also exact in float64). PRICE x10/x3.7: max\|diff\| **2.12e-11 / 3.11e-11**; VOLUME x10/x3.7: max\|diff\| **2.89e-11 / 2.74e-11** -- float64 rounding in the correlation/division chain (larger than `g191_146`'s because a rolling correlation's variance terms amplify rounding more than a single division, but still 8 orders of magnitude under the test's 1e-9 tolerance), not a scale dependency. `0 < 1,477 fires < 1,500` and `1,477 > 1` distinct values rule out a constant column |
| E Attribution | **pending** | Gate E: pending, run by issue-solver after this session |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **287 -> 288** (`volume` **34 -> 35**); `df.ta.<name>()` accessor
count **295 -> 296**. Touch points: `pandas_ta/volume/g191_191.py` (module),
`pandas_ta/volume/__init__.py` (export), `pandas_ta/__init__.py` ->
`Category["volume"]` (discovery), `pandas_ta/core.py` ->
`AnalysisIndicators.g191_191` (accessor), `tests/test_g191_191.py` (tests).
`README.md`'s headline and `volume (35)` row, and `docs/IndicatorDictionary.md`
(regenerated), both updated and checked by `tests/test_readme_counts.py`.
`docs/MLCompanionContract.md`'s running tag count updated **632 -> 633 / 275 -> 276
`SF`** (`G191_191_20_5` probes cleanly at the dictionary's 600-bar synthetic
frame and takes many distinct values, so the generator tags it `SF`);
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`
re-derives and passes against the updated `Counter`. `tests/test_altport2_ports.py`'s
`CATEGORY_TOTAL` updated to match (287 -> 288) and `CATEGORY_BUCKETS["volume"]`
(34 -> 35).

`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
now owes a row for `g191_191` (expected -- this is the "Gate E owed, not
failed" skip described in CLAUDE.md, surfaced as a hard failure in this local
run because `GATE_E_PENDING_OK` is not set outside CI). `mtd_ret` is also
owed in the same assertion, pre-existing and unrelated to this port (carried
over from issue #206, per `docs/G191146Measured.md`'s identical note).

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order: **3 failed, 4533
passed, 83 skipped**. `g191_191`'s own tests (`tests/test_g191_191.py`): **19
passed**. The three failures, all pre-existing and unrelated to this port
(CLAUDE.md "Known breaks" plus the two owed Gate E rows):
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
(owed for `['g191_191', 'mtd_ret']` -- `g191_191` is this port's own pending
row, closed by the receipt session after the launcher's Gate E run;
`mtd_ret` pre-dates this session),
`tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this worktree)
and `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
(untracked `docs/pine/` corpus). No other test regresses.
