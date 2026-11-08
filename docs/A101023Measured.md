# a101_023 — measured (issue #47)

> **Status: Gates A-E cleared, SHIP.** Gate F (both repos' suites) is run
> by the launcher in clean worktrees; `python -m pytest -q` in this
> worktree is reported below for the record.

Two-day high change above the 20-day mean high: Kakushadze's (2016, Wilmott,
"101 Formulaic Alphas") Alpha101 `#23`, per issue #47's own instruction.
Module `pandas_ta/momentum/a101_023.py`, column `A101_023_20_2`. Tests:
`tests/test_a101_023.py` (14, all passing). Numbers below:
`python docs/measure_a101_023.py`. Environment: this worktree's pinned
pandas/numpy. Measured 2026-11-08.

## Gate A: derivation from the published formula, not the prototype

Issue #47 states Alpha101 `#23`:

    mean(high, 20) < high ? -delta(high, 2) : 0

with the issue's own scale-free instruction: divide the price-unit branch by
`close`.

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- vnpy's `vnpy/alpha101` module (MIT) -- was never read. Everything below is
derived directly from the issue's own stated formula string, which needs no
ambiguous-operator resolution: `mean(x, d) = x.rolling(d).mean()`,
`delta(x, d) = x - x.shift(d)`, and the ternary is a plain
`pandas.Series.where`. Unlike `a101_021` (issue #45) and `a101_043` (issue
#46), this formula carries no `adv(d)` or `ts_rank` term, so no ASSUMPTION is
needed.

One modelling choice, not an ambiguity in the formula itself: the warm-up
re-mask. A `NaN < x` comparison is `False` in pandas, so without an explicit
re-mask the first `length - 1` bars (where `mean_h` is undefined) would read
as the ternary's literal `0` branch -- a real value, not an undefined one.
The issue's own prototype (`docs/issues/screen/ind_screen.py`'s
`(-delta(h, 2) / c).where(mean(h, 20) < h, 0.0).where(mean(h, 20).notna())`)
re-masks those bars to NaN explicitly, and this port does the same
(`result = result.where(mean_h.notna())`), so the warm-up is undefined,
not zero.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | primary vnpy/Kakushadze text NOT consulted (no `docs/pine/`/web this session) -- self-consistent against the issue's own stated formula, no ambiguous operator to resolve | 8-bar hand-derived example at `length=5, delta_length=2` (`tests/test_a101_023.py::test_hand_derived_eight_bars`), reproduced in `docs/measure_a101_023.py` (`hand-derived bars 0..7: [nan, nan, nan, nan, 0.0, -0.3684210526315789, 0.0, -0.05]`), computed by hand from the formula text, not by re-running the module |
| B Causality | pass | Future-perturbation sweep (high and close both rewritten from `j` onward), 35 offsets past the 19-bar warm-up: real module **0 of 35** leaks (`python docs/measure_a101_023.py`). A weaker mutant was tried first and rejected as under-sized: shifting the write index by `length=20` bars is a real look-ahead (proved live: output differs from the real module) but caught only **32 of 35**. The mutant actually shipped shifts the whole write index 30 bars into the future (`result = result.where(mean_h.notna()).shift(-30)`, `importlib` source read, `exec`'d in memory): shown live (differs from the real module), then caught at **35 of 35** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic walk (seed 11, sigma=1.5%/bar on close, high built as `close * (1 + abs(normal(0, sigma*0.5)))`), shipped defaults (`length=20, delta_length=2`): **1,481 of 1,500** bars non-NaN (98.73%) -- exactly `n - 19`, the `length - 1 = 19`-bar warm-up, no wider gap. **718 distinct values** observed on this walk (not a constant column); **764 of 1,500** fired bars (50.93%) read the literal `0.0` branch, the rest the price-ratio branch |
| D Scale-free | pass | A joint high/close price rescale x8/x64: **bit-identical, 0.0 max\|diff\|** (`mean_h < high` compares two quantities scaled by the identical `k`; `raw = -d2/close` scales by `k/k=1`). x10/x3.7: max\|diff\| ~2.1e-16, well under the 1e-9 tolerance the test asserts -- not bit-identical (unlike the power-of-two case, which is exact in IEEE754), but a floating-point-rounding-level difference, not a scale leak. `0 < 1,481 fires < 1,500` and `718 > 1` distinct values rule out a constant column |
| E Attribution | SHIP | max \|rho\| **0.5861** vs `HA_Body_Ratio` (manifest, n=397,158), per-frame max median 0.58894 (89 frames), band < 0.76 -- run `is47-a101_023-9694a8f1`, recorded `docs/gate_e_ledger.csv` |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **279 → 280** (`momentum` **67 → 68**); `df.ta.<name>()` accessor
count **287 → 288**. Touch points: `pandas_ta/momentum/a101_023.py` (module),
`pandas_ta/momentum/__init__.py` (export), `pandas_ta/__init__.py` →
`Category["momentum"]` (discovery), `pandas_ta/core.py` →
`AnalysisIndicators.a101_023` (accessor), `tests/test_a101_023.py` (tests).
`README.md`'s headline and `momentum (68)` row, and `docs/IndicatorDictionary.md`
(regenerated), both updated and checked by `tests/test_readme_counts.py`.
`docs/MLCompanionContract.md`'s running tag count updated **624 → 625 / 267 →
268 `SF`** (`A101_023_20_2` probes cleanly at the dictionary's 600-bar
synthetic frame and is tagged `SF` there -- confirmed by reading the
generated `docs/IndicatorDictionary.md` row directly, not re-derived by
hand); `tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`
re-derives and passes against the updated `Counter`. `tests/test_altport2_ports.py`'s
`CATEGORY_TOTAL` updated to match (279 → 280); `CATEGORY_BUCKETS` is unaffected
(it tracks only `trend`/`volatility`/`volume`, not `momentum`).

`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
passes now that the launcher's Gate E run is recorded in
`docs/gate_e_ledger.csv` (run `is47-a101_023-9694a8f1`, measured 2026-11-08).

## Suite run (this repo, this session)

Prior session (Gate E owed): `python -m pytest -q`, full suite, default
collection order: **3 failed, 4338 passed, 83 skipped**. This receipt
session, after recording the Gate E ledger row: **2 failed, 4346 passed, 83
skipped**, the ledger test now passing. The two remaining failures are
expected and unrelated to the port's own logic:
`test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this worktree)
and `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
(CLAUDE.md "Known breaks" -- untracked `docs/pine/` corpus). No other test
regresses; `tests/test_a101_023.py` alone: 14 passed.

Note: `tests/test_wiring_accessors.py`'s `strategy()`-exercising tests mutate
the module-level `Category` lists in place (`core.py`'s `strategy()` calls
`[ta.remove(x) for x in excluded if x in ta]` on the live list returned by
`_indicators_by_category`, not a copy) -- a pre-existing defect, not
introduced by this port. It only surfaces if that test module is collected
before `tests/test_readme_counts.py`/`tests/test_altport2_ports.py` in the
same process; alphabetical collection order (the default) avoids it, which is
why the full-suite run above is clean. Confirmed by running
`tests/test_wiring_accessors.py` immediately before `tests/test_altport2_ports.py`
in one process in this session: the category-total check then reads the
mutated (smaller) count and fails -- reproducing the documented defect, not a
regression from this port.

## Receipt

Gates A-E clear on the port (Gate E max |rho| 0.5861 vs `HA_Body_Ratio`,
well under the 0.76 SHIP line). SHIP: the port stays, no revert. Gate E
ledger row recorded `docs/gate_e_ledger.csv` (run `is47-a101_023-9694a8f1`,
measured 2026-11-08).
