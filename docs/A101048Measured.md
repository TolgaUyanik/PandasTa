# a101_048 — measured (issue #41)

> **Status: Gates A-D cleared this session.** Gate E: pending, run by issue-solver
> after this session. Gate F (both repos' suites) is run by the launcher in clean
> worktrees; `python -m pytest -q` in this worktree is reported below for the record.

Autocorrelation-scaled return: Kakushadze's (2016, Wilmott, "101 Formulaic Alphas")
Alpha101 `#48`, without its cross-sectional `IndNeutralize` wrapper (this fork has no
sector/industry classification to neutralise against), per issue #41's own instruction.
Module `pandas_ta/momentum/a101_048.py`, column `A101_048_250`. Tests: `tests/test_a101_048.py`
(12, all passing). Numbers below: `python docs/measure_a101_048.py`. Environment: this
worktree's pinned pandas/numpy. Measured 2026-11-08.

## Gate A: derivation from the published formula, not the prototype

Issue #41 states Alpha101 `#48` (`IndNeutralize` dropped) as:

    corr(delta(close, 1), delta(delay(close, 1), 1), 250)
        * delta(close, 1) / close
        / sum((delta(close, 1) / delay(close, 1))^2, 250)

Derived independently from Kakushadze's published operator definitions (`delta(x,n) =
x - x[n bars ago]`, `delay(x,n) = x[n bars ago]`, `corr(x,y,n)` = rolling Pearson
correlation over an `n`-bar window, `sum(x,n)` = rolling sum over an `n`-bar window), and
cross-checked against the well-known public "WorldQuant 101 Alphas" formulation of the
same Alpha#48 (`(correlation(delta(close,1), delta(delay(close,1),1), 250) *
delta(close,1)) / close) / sum((delta(close,1)/delay(close,1))^2, 250)`, with
`indneutralize` dropped), which carries the grouping explicitly in its own parentheses:

1. `delta(close, 1) = close - close.shift(1)` (`d` in the module).
2. `delay(close, 1) = close.shift(1)`, so `delta(delay(close, 1), 1) = close.shift(1) -
   close.shift(2)`, which is exactly `d.shift(1)` — i.e. the lag-1 autocorrelation of the
   daily close-change series, not a fresh computation.
3. `delta(close, 1) / delay(close, 1)` is the plain simple return `r[t] =
   close[t]/close[t-1] - 1`.
4. The grouping is `((corr(d, d.shift(1), 250) * d) / close) / sum(r^2, 250)` — exactly
   the order computed in the module. `docs/measure_a101_048.py`'s independent per-bar
   loop (built from this reading using `numpy.corrcoef`, not pandas' `.rolling().corr()`)
   matches the module to 1e-9 — see the Gate A row below.

Source cited by the issue: Kakushadze (2016, Wilmott); vnpy's `vnpy/alpha101` module
(MIT) carries the same published formula and was read only to confirm the issue's own
transcription against a second independent source, not consulted as the formula's
origin — neither `docs/pine/` nor web access is available in this worktree, so the
derivation above rests on the published operator definitions and the issue's own text.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass, derived from the published formula | Hand-derived example at `length=2` on a 6-bar series (a correlation of exactly two points is always +-1, checkable by sign alone): bars 3/4/5 read -22.885650727163167, 10.054171703465897, -17.025068828516126 by the formula's own arithmetic, not by re-running the module. Independently matches a `numpy.corrcoef`-based per-bar loop at the shipped default (`length=250`), 3 spot-checked bars (300, 350, 399) on a 400-bar synthetic walk, rel. tolerance 1e-9 |
| B Causality | pass | Future-perturbation sweep, 30 offsets past the 252-bar warm-up: real module **0 of 30** leaks. One look-ahead mutant (`importlib` source read, the autocorrelation's lag term shifted from `d.shift(1)` to `d.shift(-1)` — a 1-bar read into the future — `exec`'d in memory) is shown live (differs from the real module), then caught at **30 of 30** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic geometric walk (seed 11, σ=1.5%/bar), shipped default (`length=250`): **1,249 of 1,500** bars non-NaN (83.27%) — exactly `n - 251`, i.e. only the combined 251-bar warm-up (the length-250 rolling window plus the 1-bar lag inside the correlation) is excluded, no wider gap. 1,249 distinct values among the 1,249 (every fired bar distinct). Range [-0.090597, 0.055777], median 0.000102 |
| D Scale-free | pass | x8/x64: **bit-identical, 0.0 max\|diff\|** (every term is a ratio of identically-scaled prices, or a correlation coefficient, which is scale-invariant by definition). x10/x3.7: max\|diff\| 5.53e-16 / 6.41e-16 — both well under the 1e-9 tolerance the test asserts, with matching NaN masks. `0 < 1,249 fires < 1,500` and 1,249 distinct values rule out a constant column |
| E Attribution | pending, run by issue-solver after this session | — |
| F Suites | this repo only; parent repo (`Backtesting`) and Gate E are run by the launcher in clean worktrees | `python -m pytest -q` (this session, pre-ledger-record): **3 failed, 4238 passed, 83 skipped** — the 3 failures are all pre-existing/expected: `test_pine_coverage_csv.py` (known break, untracked `docs/pine/` corpus — see CLAUDE.md "Known breaks"), `test_altrepo_talib_csv.py` (needs the sibling `../AlternativeRepos` checkout), `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (this port's row is owed — a future receipt session records it) |

## Wiring

`Category` **275 → 276** (`momentum` **64 → 65**); `df.ta.<name>()` accessor count **283 →
284**. Touch points: `pandas_ta/momentum/a101_048.py` (module), `pandas_ta/momentum/__init__.py`
(export), `pandas_ta/__init__.py` → `Category["momentum"]` (discovery), `pandas_ta/core.py` →
`AnalysisIndicators.a101_048` (accessor), `tests/test_a101_048.py` (tests). `README.md`'s
headline and `momentum (65)` row, and `docs/IndicatorDictionary.md` (regenerated via
`python docs/gen_indicator_dictionary.py`), both updated and checked by
`tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s running tag count updated
**620 → 621 / 264 → 265 `SF`** (`A101_048_250` probes cleanly at the dictionary's 600-bar
synthetic frame — `length=250` fits inside it); `tests/test_ml_companions.py::
test_the_contract_quotes_the_dictionarys_actual_ml_form_counts` re-derives and passes against
the updated `Counter`. `tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match
(275 → 276).

## Receipt (pending)

Gate E has not run yet. A future receipt session records the launcher's run in
`docs/gate_e_ledger.csv` and fills in this section with the measured verdict, max\|ρ\| and
comparator, deciding ship vs. revert per CLAUDE.md's bands. The issue's own 2026-10-24
prototype screen (`a101_048` in `docs/issues/screen/candidates.csv`) measured the
PROTOTYPE (not this port) at max\|ρ\| 0.1851 vs `log_return` on `compute_all` (n=376,510),
top-5 per-frame max median 0.2222 → SHIP — stated here as the issue's own prior evidence
only, not re-asserted as this port's result until the launcher's run on the actual module
confirms it.
