# g191_076 — measured (issue #54)

> **Status: Gates A-D cleared, Gate E pending.** Gate E is run by the
> launcher in `../Backtesting` after this session; this file's Gate E
> section is filled in by a later receipt session once that run lands.

Variability of return-per-volume: Guotai Junan's (2017, "GTJA191", internal
quant report, read via the HKUDS/Vibe-Trading copy, MIT) alpha `#76`, per
issue #54's own instruction. Module `pandas_ta/volume/g191_076.py`, column
`G191_076_20`. Tests: `tests/test_g191_076.py` (19, all passing). Numbers
below: `python docs/measure_g191_076.py`. Environment: this worktree's
pinned pandas/numpy. Measured 2026-11-09.

## Gate A: derivation from the published formula, not the prototype

Issue #54 states GTJA191 alpha `#76`:

    STD(|C/C1-1|/V,20) / MEAN(|C/C1-1|/V,20)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. Everything below is derived
from the issue's own stated formula string, per the issue's own instruction
("Gate A starts from the source formula, not the prototype").

The formula is already a single ratio -- a rolling coefficient of variation
of `X = |C/C1-1| / V` -- so there is no grouping to resolve, unlike
`g191_191`'s `+`/`-` chain. No operator here needs a disclosed ASSUMPTION:
the issue's own prototype (`docs/issues/screen/ind_screen.py`) spells out
every operator as plain code, not prose --

    def delay(x, n): return x.shift(n)
    def ret(c): return c / c.shift(1) - 1
    def mean(x, n): return x.rolling(n).mean()
    def std(x, n): return x.rolling(n).std()
    def sdiv(a, b): return (a / b).replace([inf, -inf], nan)

-- and this port reuses those spellings directly:

    G191_076 = sdiv(STD(sdiv(|ret(C)|, V), 20), MEAN(sdiv(|ret(C)|, V), 20))

The prototype's own candidate function (`ind_screen.py:419-423`,
`cand("g191_076", ...)`) wraps BOTH divisions in `sdiv`, not bare `/`:
`x = sdiv(ret(c).abs(), v)` then `return sdiv(std(x, 20), mean(x, 20))` --
read directly off the prototype's own function body, not a guess. This port
reuses that guard at both divisions for the identical reason: a zero-volume
bar would otherwise make `X` `+-inf` rather than a defined number, and a
zero-mean window (`MEAN(X, 20) == 0`) would otherwise make the output
`+-inf` too.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula, using the prototype's own (unambiguous) `ret`/`STD`/`MEAN`/`sdiv` spellings -- no disclosed ASSUMPTION needed | 6-bar hand-derived example at `length=3` (`tests/test_g191_076.py::test_hand_derived_six_bars`), checked against an independent per-bar computation of `ret_c`/`x`/`std_x`/`mean_x`: `result[3..5] = [0.409433501628981, 0.09128569967877538, 0.16898413531713724]`, matching the module's float64 output exactly. Matches an independent per-bar loop built from plain numpy (`np.std(ddof=1)`, `np.mean` over explicit slices, not pandas' `.rolling()`) at the shipped default (`length=20`), 3 spot-checked bars (300, 600, 899) on a 900-bar synthetic close/volume series |
| B Causality | pass | Future-perturbation sweep (both close and volume series rewritten from `j` onward, another synthetic series), 34 offsets past the 20-bar warm-up: real module **0 of 34** leaks (`python docs/measure_g191_076.py`). Two independent mutants (`importlib` source read, `exec`'d in memory), each shown live (differs from the real module) then caught at **34 of 34**: shifting the whole write index `length=20` bars into the future, and computing `STD`/`MEAN` with `center=True` instead of the causal trailing window -- the same look-ahead bug class CLAUDE.md documents for `bos`'s `rolling(..., center=True)` |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic close/volume series (seed 11/23, see `docs/measure_g191_076.py:_cv`), shipped default: **1,480 of 1,500** bars non-NaN (98.67%) -- exactly `n - 20`, the `length = 20`-bar warm-up, no wider gap. **1,480 distinct values** observed on this frame (every fired bar distinct -- not a constant column), range `[0.397496, 2.395784]`, median `0.858053` |
| D Scale-free | pass | `ret_c` is exactly scale-free under a positive close rescale (`k` cancels inside `C/C1`, so price scale never reaches `x`); `x` scales by `1/k` under a positive volume rescale, and `STD`/`MEAN` are both linear in a positive scalar multiple, so `std_x / mean_x` is exactly invariant algebraically under ANY `k > 0`. Measured on the 1,500-bar series: PRICE x8/x64 **bit-identical, 0.0 max\|diff\|**; VOLUME x8/x64 **bit-identical, 0.0 max\|diff\|** (power-of-two multiplication is exact in IEEE754, so the algebraic cancellation is also exact in float64). PRICE x10/x3.7: max\|diff\| **2.22e-14 / 1.82e-14**; VOLUME x10/x3.7: max\|diff\| **8.44e-15 / 1.90e-14** -- float64 rounding from the scalar multiply itself, tighter than `g191_191`'s correlation-based ratio because this chain is two plain divisions, not a Pearson correlation's variance terms -- well under the test's 1e-9 tolerance, not a scale dependency. `0 < 1,480 fires < 1,500` and `1,480 > 1` distinct values rule out a constant column |
| E Attribution | **pending** | Gate E: pending, run by issue-solver after this session |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **288 -> 289** (`volume` **35 -> 36**); `df.ta.<name>()` accessor
count **296 -> 297**. Touch points: `pandas_ta/volume/g191_076.py` (module),
`pandas_ta/volume/__init__.py` (export), `pandas_ta/__init__.py` ->
`Category["volume"]` (discovery), `pandas_ta/core.py` ->
`AnalysisIndicators.g191_076` (accessor), `tests/test_g191_076.py` (tests).
`README.md`'s headline and `volume (36)` row, and `docs/IndicatorDictionary.md`
(regenerated), both updated and checked by `tests/test_readme_counts.py`.
`docs/MLCompanionContract.md`'s running tag count updated **633 -> 634 /
276 -> 277 `SF`** (`G191_076_20` probes cleanly at the dictionary's 600-bar
synthetic frame and takes many distinct values, so the generator tags it
`SF`). `tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match
(288 -> 289) and `CATEGORY_BUCKETS["volume"]` (35 -> 36).

`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
now owes a row for `g191_076` (expected -- this is the "Gate E owed, not
failed" skip described in CLAUDE.md, surfaced as a hard failure in this local
run because `GATE_E_PENDING_OK` is not set outside CI). `mtd_ret` is also
owed in the same assertion, pre-existing and unrelated to this port (carried
over from issue #206, per `docs/G191146Measured.md`'s identical note).

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order: **3 failed, 4560
passed, 83 skipped**. `g191_076`'s own tests (`tests/test_g191_076.py`): **19
passed**. Pre-existing failures, all unrelated to this port (CLAUDE.md
"Known breaks" plus the owed Gate E rows): `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
(owed for `['g191_076', 'mtd_ret']` -- `g191_076` is this port's own pending
row, closed by the receipt session after the launcher's Gate E run; `mtd_ret`
pre-dates this session), `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this worktree)
and `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
(untracked `docs/pine/` corpus). No other test regresses.
