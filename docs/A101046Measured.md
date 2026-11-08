# a101_046 — measured (issue #49)

> **Status: Gates A-D cleared on the port.** Gate E: pending, run by
> issue-solver after this session. Gate F (both repos' suites) is run by
> the launcher in clean worktrees; `python -m pytest -q` in this worktree is
> reported below for the record.

10-day price acceleration: Kakushadze's (2016, Wilmott, "101 Formulaic
Alphas") Alpha101 `#46`, per issue #49's own instruction -- the "core"
sub-expression shared with `#49`/`#51`. Module
`pandas_ta/momentum/a101_046.py`, column `A101_046_10`. Tests:
`tests/test_a101_046.py` (14, all passing). Numbers below: `python
docs/measure_a101_046.py`. Environment: this worktree's pinned
pandas/numpy. Measured 2026-11-08.

## Gate A: derivation from the published formula, not the prototype

Issue #49 states the Alpha101 `#46`/`#49`/`#51` core:

    (delay(close, 20) - delay(close, 10)) / 10 - (delay(close, 10) - close) / 10

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- vnpy's `vnpy/alpha101` module (MIT) -- was never read. Everything below
is derived directly from the issue's own stated formula string, which needs
no ambiguous-operator resolution: `delay(x, d) = x.shift(d)` is the only
operator present, already established by `a101_021`/`a101_023`/`a101_043`/
`a101_048`/`a101_053`.

One modelling choice, not an ambiguity in the formula itself: Kakushadze's
full Alpha101 `#46` wraps this core in a ternary on fixed price-unit
thresholds (0.25, 0, -0.1, -0.05), branching to `-1`, `+1` or a plain 1-bar
price change -- those thresholds are NOT transcribed by the issue, which
names them only to say they are dropped ("the alphas' price-unit thresholds
(0.25, 0, -0.1, -0.05) dropped"). Per the issue's own instruction, this port
ships the bare core, scale-free (divided by `close`) -- the same move
already made for `a101_023` (issue #47): "scale-free form (issue's own
instruction): divide the price-unit branch by `close`."

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | primary vnpy/Kakushadze text NOT consulted (no `docs/pine/`/web this session) -- self-consistent against the issue's own stated formula, no ambiguous operator to resolve | 12-bar hand-derived example at `length=2` (`tests/test_a101_046.py::test_hand_derived_twelve_bars`), reproduced in `docs/measure_a101_046.py` (`hand-derived bars 0..11: [nan, nan, nan, nan, -0.2777777777777778, -0.0625, 0.2692307692307692, 0.2857142857142857, -0.06666666666666667, -0.125, 0.075, -1.3]`), computed by hand from the formula text, not by re-running the module |
| B Causality | pass | Future-perturbation sweep (close rewritten from `j` onward), 37 offsets past the 20-bar warm-up: real module **0 of 37** leaks (`python docs/measure_a101_046.py`). The shipped mutant shifts the whole write index 30 bars into the future (`result = (raw / close).shift(-30)`, `importlib` source read, `exec`'d in memory): shown live (differs from the real module), then caught at **37 of 37** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic walk (seed 11, sigma=1.5%/bar on close), shipped default (`length=10`): **1,480 of 1,500** bars non-NaN (98.67%) -- exactly `n - 2*length`, the `2*length=20`-bar warm-up. **1,480 distinct values** observed (not a constant column) |
| D Scale-free | pass | A close price rescale x8/x64: **bit-identical, 0.0 max\|diff\|** (`far`, `near` and `close` are all price-unit and scale identically by a positive `k`, so `raw` scales by `k` and `raw/close` cancels it exactly). x10/x3.7: max\|diff\| **3.56e-17** / **3.73e-17** -- NOT bit-identical (floating-point-rounding level, not a scale leak), well under the 1e-9 tolerance the test asserts. `0 < 1,480 fires < 1,500` and `1,480 > 1` distinct values rule out a constant column |
| E Attribution | pending, run by issue-solver after this session | -- |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **281 → 282** (`momentum` **69 → 70**); `df.ta.<name>()` accessor
count **289 → 290**. Touch points: `pandas_ta/momentum/a101_046.py` (module),
`pandas_ta/momentum/__init__.py` (export), `pandas_ta/__init__.py` →
`Category["momentum"]` (discovery), `pandas_ta/core.py` →
`AnalysisIndicators.a101_046` (accessor), `tests/test_a101_046.py` (tests).
`README.md`'s headline and `momentum (70)` row, and `docs/IndicatorDictionary.md`
(regenerated), both updated and checked by `tests/test_readme_counts.py`.
`docs/MLCompanionContract.md`'s running tag count updated **626 → 627 / 269 →
270 `SF`** (`A101_046_10` probes cleanly at the dictionary's 600-bar synthetic
frame and is tagged `SF` there -- confirmed by reading the generated
`docs/IndicatorDictionary.md` row directly, not re-derived by hand);
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`
re-derives and passes against the updated `Counter`. `tests/test_altport2_ports.py`'s
`CATEGORY_TOTAL` updated to match (281 → 282); `CATEGORY_BUCKETS` is unaffected
(it tracks only `trend`/`volatility`/`volume`, not `momentum`).

`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails in this worktree until the launcher's Gate E run is recorded into
`docs/gate_e_ledger.csv` -- expected per this session's own instructions
("Gate E owed, run by issue-solver"); a later receipt session fills in the
measured numbers above and records the ledger row.

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order: **3 failed,
4380 passed, 83 skipped**. `tests/test_a101_046.py` alone: 14 passed.

Three failures, all pre-existing/expected and unrelated to this port's own
logic: `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this worktree),
`test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
(CLAUDE.md "Known breaks" -- untracked `docs/pine/` corpus), and
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
(Gate E owed for `a101_046`, as disclosed above -- the next session's
receipt clears it once the launcher's run is recorded).

## Receipt

Gates A-D clear on the port (hand-derived correctness, 0/37 causality leaks
with the mutant caught at 37/37, bit-identical x8/x64 scale invariance,
measured 3.6e-17-level x10/x3.7 tolerance). Gate E is owed; this file is the
receipt for what was measured this session, and a later session records the
launcher's Gate E run and the final ship/revert verdict.
