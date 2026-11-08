# a101_035 — measured (issue #50)

> **Status: Gates A-D cleared in this session. Gate E: pending, run by issue-solver
> after this session.** Gate F (both repos' suites) is also run by the launcher in
> clean worktrees; `python -m pytest -q` in this worktree is reported below for the
> record.

Volume rank x price rank x return rank: Kakushadze's (2016, Wilmott, "101 Formulaic
Alphas") Alpha101 `#35`, per issue #50. Module `pandas_ta/volume/a101_035.py`, column
`A101_035_32_16_32`. Tests: `tests/test_a101_035.py` (17, all passing). Numbers below:
`python docs/measure_a101_035.py`. Environment: this worktree's pinned pandas/numpy.
Measured 2026-11-08.

## Gate A: derivation from the published formula, not the prototype

Issue #50 states Alpha101 `#35`:

    ts_rank(volume, 32) * (1 - ts_rank(close + high - low, 16)) * (1 - ts_rank(returns, 32))

**What this session could NOT do, disclosed up front:** `docs/pine/` and web access are
both unavailable in this worktree, so the issue's own named copy -- vnpy's `vnpy/alpha101`
module (MIT) -- was never read. Everything below is derived from the issue's own
restated formula and from this fork's already-shipped operators, not from vnpy or from
Kakushadze's original paper text. Unlike `a101_048`/`a101_058`, this formula carries no
`IndNeutralize` wrapper and no `vwap` substitution to resolve -- it is already stated in
terms of plain `close`/`high`/`low`/`volume`.

1. `ts_rank(x, d)` = the percentile rank of the current bar within its own trailing
   `d`-bar window: `count(x[t-d+1..t] <= x[t]) / d`. **ASSUMPTION, disclosed, carried over
   unchanged from `a101_058`** (issue #42): Kakushadze's glossary names the operator but
   does not spell out tie handling or normalisation, so this fork's own existing
   convention -- shared with `pandas_ta.statistics.rank`'s `RANK_d` (issue #34, a port of
   qlib's `Rank`) -- is reused here for internal consistency, not independently
   re-derived from vnpy.
2. `returns` = the plain one-bar simple return, `close[t] / close[t-1] - 1`. Taken
   directly: `a101_048` (issue #41) already established `close.pct_change(fill_method=
   None)` as this fork's convention for the identical quantity.
3. `close + high - low` is read literally off the formula string -- no operator to
   resolve, just addition and subtraction of the three price series.

No cross-sectional `IndNeutralize` appears in the issue's stated formula for `#35`
(unlike `#48`/`#58`), so nothing was dropped here.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | primary vnpy/Kakushadze text NOT consulted (no `docs/pine/`/web this session) -- self-consistent against the issue's own stated formula, built entirely from already-shipped, already-tested primitives (this fork's own `ts_rank` convention from `rank.py`/`a101_058`, and `a101_048`'s `returns` convention) | Hand-derived 8-bar example at `vol_length=3, price_length=2, return_length=3` (`high - low` held at a constant 1.0 so `close + high - low` is a monotonic shift of `close`, same rank order): bars 3,5,7 read exactly 0.0, bars 4 and 6 read exactly 1/9, derived by hand from the formula, not by re-running the module. Matches an independent plain-Python loop (`sum`/comparisons, not `numpy.lib.stride_tricks`) at the shipped defaults (`vol_length=32, price_length=16, return_length=32`), 3 spot-checked bars (300, 500, 899) on a 900-bar synthetic walk, rel. tolerance 1e-9 |
| B Causality | pass | Future-perturbation sweep (all of high/low/close/volume rewritten from `j` onward), 15 offsets past the 32-bar warm-up on a 900-bar frame: real module **0 of 15** leaks (`tests/test_a101_035.py`); the measure script runs the wider 30-offset sweep on a 1,500-bar frame, same result (**0 of 30**, `python docs/measure_a101_035.py`). A 1-bar look-ahead was tried FIRST as the mutant and rejected: caught only **29 of 30** offsets -- `ts_rank`'s integer-count quantisation sometimes absorbs a 1-bar perturbation without changing bucket, a quantisation artefact of the rank steps, not a causality gap. The mutant actually shipped wraps the whole final write (`result = vol_rank * (1 - pr_rank) * (1 - ret_rank)`) in `.shift(-vol_length)` -- a full 32-bar look-ahead (`importlib` source read, `exec`'d in memory): shown live (differs from the real module), then caught at **30 of 30** (measure script) / every offset (test module, 15 of 15) |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic walk (seed 11, σ=1.5%/bar close, σ=1.95%/bar volume), shipped defaults: **1,468 of 1,500** bars non-NaN (97.87%) -- exactly `n - 32`, the `max(vol_length-1, price_length-1, return_length) = 32`-bar combined warm-up (first valid index 32), no wider gap. **674 distinct values** among the 1,468 fired bars, min 0.0, max 0.908203, median 0.038086 -- not degenerate |
| D Scale-free | pass | x8/x64 on EITHER high/low/close OR volume independently: **bit-identical, 0.0 max\|diff\|** (`ts_rank` is a pure order statistic, invariant to any positive rescale of its input; `returns` cancels the price scale exactly). x10/x3.7 on either input: **also 0.0 max\|diff\|**, measured rather than merely asserted -- these are not powers of two, so exact IEEE754 cancellation in `returns`' division is not a mathematical certainty the way x8/x64 is, but no tie in the tested windows flipped under the ~1e-16-scale rounding this frame produced (see the module docstring's SCALE-FREE paragraph for the caveat that this is an empirical finding on this frame, not a universal guarantee). `0 < 1,468 fires < 1,500` and 674 distinct values rule out a constant column |
| E Attribution | **pending, run by issue-solver after this session** | not run in this worktree; the issue's own prototype screen (`docs/issues/screen/candidates.csv`) measured max\|ρ\| 0.7140 vs `Dist_to_FWMA_pct` (n=396,001), per-frame max median 0.7093 -> SHIP (< 0.76 ship line) -- that number describes the PROTOTYPE, not this port, and is not treated as this port's result |
| F Suites | this repo only; parent repo (`Backtesting`) and Gate E are run by the launcher in clean worktrees | `python -m pytest -q` (this session): **3 failed, 4405 passed, 83 skipped** -- all three failures pre-existing/expected and unrelated to this port: `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (this port's row is owed, recorded by a later receipt session once the launcher's Gate E run lands), `test_pine_coverage_csv.py` (known break, untracked `docs/pine/` corpus -- see CLAUDE.md "Known breaks"), `test_altrepo_talib_csv.py` (needs the sibling `../AlternativeRepos` checkout) |

## Wiring

`Category` **282 → 283** (`volume` **32 → 33**); `df.ta.<name>()` accessor count **290 →
291**. Touch points: `pandas_ta/volume/a101_035.py` (module), `pandas_ta/volume/__init__.py`
(export), `pandas_ta/__init__.py` → `Category["volume"]` (discovery), `pandas_ta/core.py` →
`AnalysisIndicators.a101_035` (accessor), `tests/test_a101_035.py` (tests). `README.md`'s
headline and `volume (33)` row, and `docs/IndicatorDictionary.md` (regenerated), both
updated and checked by `tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s
running tag count updated **627 → 628 / 270 → 271 `SF`** (`A101_035_32_16_32` probes
cleanly at the dictionary's 600-bar synthetic frame -- the 32-bar warm-up fits trivially);
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`
re-derives and passes against the updated `Counter`. `tests/test_altport2_ports.py`'s
`CATEGORY_TOTAL` updated to match (282 → 283) and `CATEGORY_BUCKETS["volume"]`
updated (32 → 33), since that test pins the exact per-category count.

## Receipt

Gate A-D cleared this session (2026-11-08), all measured above, not merely asserted. Gate
E has not run: this worktree has no access to the parent repo's Gate E harness by design
(the launcher runs it separately). This file stands as the receipt for Gates A-D; a later
receipt session fills in the Gate E numbers once the launcher's run lands, decides
SHIP/DISCLOSE/STRUCK per CLAUDE.md's bands, and records the row in
`docs/gate_e_ledger.csv`. The issue's own 2026-10-24 prototype screen measured the
PROTOTYPE (not this port) at max|ρ| 0.7140 vs `Dist_to_FWMA_pct` -> SHIP; this port's own
Gate E run is the number that will actually decide ship vs. revert, per CLAUDE.md's "Owed,
not failed" policy.
