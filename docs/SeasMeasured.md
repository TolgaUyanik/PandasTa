# Heston-Sadka Annual-lag Seasonality — measured (`seas`)

At bar T, the return over the next `length` bars, measured `years` trading years (252 bars
each) ago, averaged. Found by the ResearchIntel RAG scan of 2026-10-24, round 3 (issue
#27). Sources: Quantpedia strategy 0125 "12 Month Cycle in Cross-Section of Stocks
Returns" (SSRN 687022, T2); Flirting with Models' "Seasonality Everywhere" (T3); Kaufman
2013 ch.10, Quantpedia's Hirshleifer-Jiang-Meng mood-beta screen (both cross-sectional, T3).

**Status: Gates A-F cleared. Verdict: SHIP** (`SEAS_21_1`, max |ρ| 0.3245 vs `Mom_12_1_pct`,
n=376,421, far under the 0.76 ship line). `seas` is in `Category`, so any `df.ta.strategy()`
sweep in the parent repo picks it up.

Shipped: `pandas_ta/performance/seas.py`, one column `SEAS_<length>_<years>` (default
`SEAS_21_1`), unbounded (a mean of price-ratio returns). Tests: `tests/test_seas.py` (15).
Numbers: `python docs/measure_seas.py`. Environment: pandas 2.3.3, numpy (repo-pinned),
Python 3.11. Measured 2026-11-01.

## Gate A decisions (no clarification channel in this session)

The issue leaves two choices open and says "decide at Gate A." Read conservatively --
smaller-scope reading wins per the issue-solver rules, no owner answer available:

- **`years` defaults to 1**, not 5. 1 is Quantpedia's own version (the issue's T2
  citation, the strongest evidence) and needs a 252-bar warm-up instead of 1,260. `years`
  is a free parameter, so `SEAS_21_5` is still reachable by passing `years=5`; it is just
  not the default `df.ta.strategy()` sweeps.
- **Bar-count year (252 bars), not a `DatetimeIndex`-anchored one.** The issue's own risk
  note calls the date-anchored version a separate design that "needs a `DatetimeIndex`" --
  the larger-scope option. The formula as given in the issue (`T - 252*y + h`) is itself
  bar-count, so this ships the formula literally rather than reinterpreting it.
- **`length` is capped at 252** (`RATE["TRADING_DAYS_PER_YEAR"]`, raises `ValueError`
  above it): at `years=1` a longer window would read `close[T - 252 + length]` with
  `length > 252`, i.e. a bar after T. The cap is enforced once, at the smallest `y` (1);
  every larger `y` has strictly more slack, so the one check covers every term.

No Pine or TA-Lib source exists for this one -- it is a published cross-sectional academic
measure, not a chart script -- so Gate A is checked against an independent loop written
from the formula (`r_y(T) = close[T - 252y + h] / close[T - 252y] - 1`, SEAS = mean over
`y`) and two hand-built closes that isolate the exact bars each `r_y` reads, not a line
citation.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass (self-consistency; no source oracle for this cross-sectional measure) | hand-built 253-bar close (only `close[0]` and `close[21]` set; rest filler) reads exactly 0.10 at bar 252 for `SEAS_21_1`; a second hand-built case with two controlled lags gives `SEAS_21_2 = (0.10 + (-0.20)) / 2` exactly; matches an independent Python loop to 1e-9 on a 900-bar walk for `years` 1 and 2 |
| B Causality | pass | 31-offset future-perturbation sweep (spike + ×1000-rescale future, past the 252-bar warm-up): real module 0 leaks. Two look-ahead mutants (`numerator`, `denominator`: each pushes one `shift()` argument negative, so it reads a bar strictly after T) are each proved live, then caught at 31 of 31 |
| C Reachability | pass (real data, from Gate E run) | synthetic: 1,200-bar walk (seed 11, σ=0.015, no tick rounding), default `length=21, years=1`: 948 of 1,200 bars non-NaN (the 252-bar warm-up), all 948 nonzero, 513 positive / 435 negative, 948 distinct values, range [-0.1472, +0.1882]. Same walk tick-rounded (0.05): 948 non-NaN, 944 nonzero (509 positive / 435 negative / 4 zero). **Real data** (89 BIST frames, pooled 398,849 bars, Gate E run `is27-seas-93ce5424`): 376,421 non-NaN (398,849 − 376,421 = 22,428 = 89 × 252, the per-frame warm-up, exactly), of which 370,859 nonzero (98.5%) |
| D Scale-free | pass | x8/x64 bit-identical (each `r_y` is a price ratio minus one, exact under a power of two); x10/x3.7 max abs diff measured **2.220e-16** (one ulp); NaN masks match in both; `0 < 948 fires < 1200`, 948 distinct values rules out a constant column |
| E Attribution | **SHIP** | `gate_e_overlap.py run --module pandas_ta.performance.seas --name seas`, 89 BIST frames, 687 comparators (329 `compute_all` + 358 manifest), run `is27-seas-93ce5424`, measured 2026-11-01. `SEAS_21_1`: pooled max \|ρ\| **0.3245** against `Mom_12_1_pct` (manifest), n=376,421; per-frame max median \|ρ\| **0.3235** (also `Mom_12_1_pct`), 0 of 89 frames ≥ 0.90. Both far under the 0.76 `r3-perframe-0.90` ship line -> **SHIP** |
| F Suites | this repo only; parent repo not run by this session | `python -m pytest -q`: 3 failed / 3,893 passed / 83 skipped. Two pre-exist this port and are named in `CLAUDE.md`'s Known breaks: `test_pine_coverage_csv::test_audited_rows_carry_their_evidence` (`docs/pine/` untracked) and `test_altrepo_talib_csv::test_regenerating_reproduces_the_committed_rows` (needs the sibling `../AlternativeRepos` checkout, not on this machine). The third, `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, is the expected "Gate E owed" failure per the issue-solver rules -- it clears once the launcher's Gate E row is recorded |

## Proxy overlap (NOT Gate E)

The issue names the overlap candidates itself: a calendar `month` column (same value for
every ticker -- not a meaningful Spearman comparator) and `Ret_252d_pct`, "the cumulative
12-month return, not the one window a year ago" -- i.e. `percent_return(close, 252)`. Both
are engine-only; this package does not ship `Ret_252d_pct`, so the proxy recomputes it from
this package's own `percent_return`. Spearman ρ of `SEAS_21_1` against it, and against the
unlagged same-length return, on the same seed=11, σ=0.015, 1,200-bar synthetic walk used
for Gate C/D above (no tick rounding), n=948:

| comparator | ρ |
|---|---|
| `percent_return(252)` (proxy for `Ret_252d_pct`) | 0.3585 |
| `percent_return(21)`, unlagged (same shape, no annual lag) | 0.1547 |

Both are far below CLAUDE.md's 0.76 ship line on this synthetic probe, consistent with the
issue's own read of the engine overlap ("not the one window a year ago" -- a different
window). This is not Gate E -- one synthetic random walk, not 89 BIST frames, and a random
walk has no real annual seasonality to correlate against in the first place, so a low ρ
here is close to the null expectation either way. The real Gate E run decides.

## Closed

Gate E ran 2026-11-01 (`is27-seas-93ce5424`), recorded in `docs/gate_e_ledger.csv`.
`SEAS_21_1` max |ρ| 0.3245 is under the 0.76 ship line -> **SHIP**, no column removed.
Gates A-F all cleared; issue #27 closes as a ship.
