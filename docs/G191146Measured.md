# g191_146 — measured (issue #52)

> **Status: Gates A-E cleared, SHIP.** Gate E measured 2026-11-09 (below).
> Gate F (both repos' suites) is run by the launcher in clean worktrees;
> `python -m pytest -q` in this worktree is reported below for the record.

Return-innovation momentum: Guotai Junan's (2017, "GTJA191", internal quant
report, read via the HKUDS/Vibe-Trading copy, MIT) alpha `#146`, per issue
#52's own instruction. Module `pandas_ta/momentum/g191_146.py`, column
`G191_146_61_2_20_60_2`. Tests: `tests/test_g191_146.py` (16, all passing).
Numbers below: `python docs/measure_g191_146.py`. Environment: this
worktree's pinned pandas/numpy. Measured 2026-11-09.

## Gate A: derivation from the published formula, not the prototype

Issue #52 states GTJA191 alpha `#146`:

    MEAN(r - SMA(r,61,2), 20) * (r - SMA(r,61,2)) / SMA((r - SMA(r,61,2))^2, 60, 2)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. Everything below is derived
from the issue's own stated formula string, per the issue's own instruction
("Gate A starts from the source formula, not the prototype").

No operator here needs a disclosed ASSUMPTION, unlike `a101_007`/`a101_021`
(Alpha101 ports, where the formula's own glossary was unavailable and a
reading had to be chosen): the issue's own prototype
(`docs/issues/screen/ind_screen.py`) spells out GTJA's `SMA` convention
verbatim in its own module docstring --

    def sma(x, n, m):
        """GTJA SMA(A,n,m): Y = (m*A + (n-m)*Y[-1]) / n, an EMA with alpha m/n."""
        return x.ewm(alpha=m / n, adjust=False).mean()

-- and `ret(c): c / c.shift(1) - 1` for the return and `mean(x, n):
x.rolling(n).mean()` for the plain rolling mean. This port reuses those
spellings directly rather than re-deriving them, with one addition not
present in the prototype: `min_periods=n` on the `ewm` calls, masking the
first `n-1` bars where the recursion is dominated by its own seed value
rather than by the formula's steady-state behaviour -- the same convention
this fork's own `pandas_ta.overlap.rma`/`wilder_rma` already use for their
own `ewm(alpha=...)` calls, and a stricter warm-up than the prototype (built
only to screen Gate E, not to ship) applies.

The one naming hazard worth flagging explicitly: GTJA's `SMA(A, n, m)` is
NOT this fork's own `pandas_ta.overlap.sma` (a plain simple moving average)
-- the two share a name by historical accident of the source report, not by
design, and the module docstring calls this out so a future reader does not
"fix" the port by importing the wrong `sma`.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula, using the prototype's own (unambiguous) `SMA`/`MEAN`/`ret` spellings -- no disclosed ASSUMPTION needed | 8-bar hand-derived example at `smooth1_length=3, smooth1_weight=1, mean_length=2, smooth2_length=2, smooth2_weight=1` (`tests/test_g191_146.py::test_hand_derived_eight_bars`), replayed independently with Python's exact `fractions.Fraction` (no floats, no pandas `.ewm()`/`.rolling()`) in `docs/measure_g191_146.py`: exact bars 3..7 = `[None, 0.17635843660629172, 0.34241833560839685, -0.04556768211615564, 0.34738148161854115]`, matching the module's float64 output to ~1e-15. Matches an independent per-bar loop built from plain Python (not pandas' `.ewm()`/`.rolling()`) at the shipped defaults (`smooth1_length=61, smooth1_weight=2, mean_length=20, smooth2_length=60, smooth2_weight=2`), 3 spot-checked bars (300, 600, 899) on a 900-bar synthetic walk |
| B Causality | pass | Future-perturbation sweep (close rewritten from `j` onward, another synthetic walk), 34 offsets past the 120-bar warm-up: real module **0 of 34** leaks (`python docs/measure_g191_146.py`). Two independent mutants (`importlib` source read, `exec`'d in memory), each shown live (differs from the real module) then caught at **34 of 34**: shifting the whole write index `smooth2_length=60` bars into the future (`result = result.where(mask).shift(-smooth2_length)`), and computing `MEAN(e, mean_length)` with `center=True` instead of the causal trailing window -- the same look-ahead bug class CLAUDE.md documents for `bos`'s `rolling(..., center=True)` |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic walk (seed 11, sigma=1.5%/bar close), shipped defaults: **1,380 of 1,500** bars non-NaN (92.00%) -- exactly `n - 120`, the `smooth1_length + max(mean_length, smooth2_length) - 1 = 120`-bar warm-up, no wider gap. **1,380 distinct values** observed on this walk (every fired bar distinct -- not a constant column), range `[-0.867080, 0.895460]`, median `0.011526` |
| D Scale-free | pass | `r = close/close.shift(1) - 1` is exactly invariant under a positive rescale of `close` (the scale cancels algebraically), so the whole chain is too, as a mathematical certainty. Measured on the 1,500-bar walk: x8/x64 **bit-identical, 0.0 max\|diff\|** (power-of-two multiplication is exact in IEEE754, so the algebraic cancellation is also exact in float64). x10/x3.7: **max\|diff\| 7.77e-15 / 7.38e-15** -- float64 rounding in the division chain (of the same order as machine epsilon times the operand magnitudes), not a scale dependency; well inside the test's 1e-9 tolerance. `0 < 1,380 fires < 1,500` and `1,380 > 1` distinct values rule out a constant column |
| E Attribution | **SHIP** | `gate_e_overlap.py run --module pandas_ta.momentum.g191_146`, launcher run `is52-g191_146-717b79c3`, 89 ALTPORT-1 frames, n=388,169 pooled bars, 687 comparators (329 compute_all + 358 manifest). `G191_146_61_2_20_60_2`: max\|rho\| **0.22798** vs `BB_Bars_Above_Upper` (manifest), per-frame max median \|rho\| **0.22904** (also vs `BB_Bars_Above_Upper`, 0.0% of 89 frames >= 0.90) -- both well under the 0.76 SHIP line. Recorded in `docs/gate_e_ledger.csv`. |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **286 -> 287** (`momentum` **71 -> 72**); `df.ta.<name>()` accessor
count **294 -> 295**. Touch points: `pandas_ta/momentum/g191_146.py` (module),
`pandas_ta/momentum/__init__.py` (export), `pandas_ta/__init__.py` ->
`Category["momentum"]` (discovery), `pandas_ta/core.py` ->
`AnalysisIndicators.g191_146` (accessor), `tests/test_g191_146.py` (tests).
`README.md`'s headline and `momentum (72)` row, and `docs/IndicatorDictionary.md`
(regenerated), both updated and checked by `tests/test_readme_counts.py`.
`docs/MLCompanionContract.md`'s running tag count updated **631 -> 632 / 274 -> 275
`SF`** (`G191_146_61_2_20_60_2` probes cleanly at the dictionary's 600-bar synthetic
frame and takes many distinct values, so the generator tags it `SF`);
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`
re-derives and passes against the updated `Counter`. `tests/test_altport2_ports.py`'s
`CATEGORY_TOTAL` updated to match (286 -> 287); `CATEGORY_BUCKETS` is unaffected
(it tracks only `trend`/`volatility`/`volume`, not `momentum`).

`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
no longer owes a row for `g191_146`: the launcher's Gate E run (`is52-g191_146-717b79c3`)
is recorded in `docs/gate_e_ledger.csv` by this receipt session (2026-11-09).

## Suite run (this repo, this receipt session, after recording the Gate E row)

`python -m pytest -q`, full suite, default collection order: **3 failed, 4513
passed, 83 skipped**. `g191_146`'s own tests (`tests/test_g191_146.py`): **16
passed**. `g191_146` no longer owes a Gate E ledger row (recorded above);
the three remaining failures are unrelated to this port (CLAUDE.md "Known
breaks" plus one pre-existing, unrelated owed row):
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
(owed for `['mtd_ret']` only -- pre-dates this session, not this port),
`tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this worktree)
and `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
(untracked `docs/pine/` corpus). No other test regresses.
