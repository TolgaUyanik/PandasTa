# g191_165 — measured (issue #55)

> **Status: shipped. Gate E measured 2026-11-09, SHIP (max |rho| 0.4123 < 0.76).**

Rescaled range R/S (48): Guotai Junan's (2017, "GTJA191", internal quant
report, read via the HKUDS/Vibe-Trading copy, MIT) alpha `#165`, per issue
#55's own instruction. Module `pandas_ta/statistics/g191_165.py`, column
`G191_165_48`. Tests: `tests/test_g191_165.py` (16, all passing). Numbers
below: `python docs/measure_g191_165.py`. Environment: this worktree's
pinned pandas/numpy. Measured 2026-11-09.

## Gate A: derivation from the published formula, not the prototype

Issue #55 states GTJA191 alpha `#165`:

    MAX(SUMAC(C-MEAN(C,48))) - MIN(SUMAC(C-MEAN(C,48))) / STD(C,48)

with the issue's own parenthetical: "scale-free form: read as (MAX-MIN)/STD,
the R/S statistic; the literal precedence is price-unit".

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. Everything below is derived
from the issue's own stated formula string plus its own parenthetical
instruction, per the issue's own rule ("Gate A starts from the source
formula, not the prototype").

The parenthetical already names the target quantity: the classical
rescaled-range (R/S) statistic (Hurst, 1951) over a trailing window --

    m   = mean(window)
    d_i = window_i - m
    Z_i = cumsum(d)_i        (window-local, resets at every window boundary)
    R   = max(Z) - min(Z)
    S   = std(window)
    G191_165 = R / S

Two sub-choices the literal text leaves open, each resolved with its
reasoning, not a silent guess (full reasoning in the module docstring):

1. **Window-local vs. global `SUMAC`.** "The R/S statistic" names one
   textbook definition, and it resets the cumulative sum at each window's
   start. The issue's own prototype (`docs/issues/screen/ind_screen.py:159-
   163`, `w_rescaled_range`) independently reaches the same reading
   (`roll(c, 48, w_rescaled_range)`, `ind_screen.py:530`, windows first,
   cumsum's only inside each window). Two independent reads agree.
2. **`STD`'s ddof.** Of the sibling GTJA191 ports, only `g191_076`'s own
   formula (`STD(|C/C1-1|/V,20) / MEAN(...)`) actually invokes a `STD`
   operator; `g191_146` and `g191_191`'s formulas never do, so they are
   silent on this question, not corroborating witnesses. `g191_076` cites
   the prototype's own GENERIC `std` operator (`ind_screen.py:48`,
   `x.rolling(n).std()`, pandas default `ddof=1`) as what GTJA's `STD(...)`
   means -- the operator the formula string itself names. The prototype's
   `w_rescaled_range` helper recomputes the window's std inline with plain
   numpy (`ddof=0`) as a vectorisation shortcut local to that one screening
   function, never restated as what `STD` means anywhere else. This port
   uses `ddof=1`, matching `g191_076`'s own `STD` -- a one-port precedent,
   not a fork-wide one. The two conventions differ only by a constant
   factor `sqrt((length-1)/length)` (measured below).

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula plus its own parenthetical naming the target as "the R/S statistic" -- two disclosed interpretation choices (window-local `SUMAC`, `STD` ddof=1), both reasoned above, neither a silent guess | 7-bar hand-derived example at `length=4` (`tests/test_g191_165.py::test_hand_derived_seven_bars`), checked against an independent per-bar PYTHON LOOP (not the module's own vectorised `sliding_window_view` code): `result[3..6] = [1.5491933384829668, 1.224744871391589, 1.224744871391589, 1.5491933384829668]`, matching the module's float64 output exactly. Matches the same independent loop at the shipped default (`length=48`), 3 spot-checked bars (300, 600, 899) on a 900-bar synthetic close series, relative difference 1.6e-14 / 3.2e-15 / 5.0e-15 (float64 rounding, not a disagreement) |
| B Causality | pass | Future-perturbation sweep (close series rewritten from `j` onward, another synthetic series), 34 offsets past the 48-bar warm-up: real module **0 of 34** leaks (`python docs/measure_g191_165.py`). Two independent mutants (`importlib` source read, `exec`'d in memory), each shown live (differs from the real module) then caught at **34 of 34**: shifting the whole write index `length=48` bars into the future, and writing each window's result to its CENTER bar instead of its last bar -- the same look-ahead bug class CLAUDE.md documents for `bos`'s `rolling(..., center=True)`, expressed here as a write-index shift because this module computes its own windows with `sliding_window_view` rather than pandas' `.rolling()` |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic close series (seed 11, see `docs/measure_g191_165.py:_cv`), shipped default: **1,453 of 1,500** bars non-NaN (96.87%) -- exactly `n - 47`, the `length = 48`-bar warm-up (first valid index 47), no wider gap. **1,453 distinct values** observed (every fired bar distinct -- not a constant column), range `[10.156818, 22.540253]`, median `18.515885` |
| D Scale-free | pass | Every term in the ratio -- the window mean, the deviations, the window-local cumsum, its range, and the window's own std -- scales EXACTLY linearly with a positive rescale of `close` by any `k`, so `R / S` is exactly invariant algebraically for ANY `k > 0`. Measured on the 1,500-bar series: PRICE x8/x64 **bit-identical, 0.0 max\|diff\|** (power-of-two multiplication is exact in IEEE754, so the algebraic cancellation is also exact in float64); PRICE x10/x3.7: max\|diff\| **3.80e-13 / 4.35e-13** -- float64 rounding from the scalar multiply itself, well under the test's 1e-9 tolerance, not a scale dependency. `0 < 1,453 fires < 1,500` and `1,453 > 1` distinct values rule out a constant column. The `0/0` edge case (a `length`-bar flat run makes both the range and the std exactly zero) is guarded with `np.errstate` and pinned directly: a 60-bar constant-close series (`tests/test_g191_165.py::test_flat_window_is_nan_not_inf_or_a_crash`) fires `NaN`, never `inf`/`-inf`, at every one of its 13 would-be bars. Separately measured: the `ddof=1` vs. `ddof=0` STD choice (Gate A, point 2) scales the whole column by a constant `sqrt(47/48) = 0.989529` at the shipped default -- confirmed by direct computation, not merely the algebraic prediction |
| E Attribution | SHIP | `G191_165_48`: max \|rho\| **0.4123** vs `ADX` (`compute_all`, n = 394,666); per-frame max median \|rho\| **0.4158** (89 frames), 0.0% of frames >= 0.90. Run `is55-g191_165-3ddebe03`, `../Backtesting/Backtesting/scripts/analysis/gate_e_overlap.py run --module pandas_ta.statistics.g191_165`, canary bit-equal (AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS). Band `r3-perframe-0.90`: SHIP < 0.76 -- clears it with room to the DISCLOSE line. Ledger row recorded in `docs/gate_e_ledger.csv` (`python docs/gate_e_ledger.py record ... --measured 2026-11-09`) |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **289 -> 290** (`statistics` **23 -> 24**); `df.ta.<name>()`
accessor count **297 -> 298**. Touch points:
`pandas_ta/statistics/g191_165.py` (module),
`pandas_ta/statistics/__init__.py` (export), `pandas_ta/__init__.py` ->
`Category["statistics"]` (discovery), `pandas_ta/core.py` ->
`AnalysisIndicators.g191_165` (accessor), `tests/test_g191_165.py` (tests).
`README.md`'s headline and `statistics (24)` row, and
`docs/IndicatorDictionary.md` (regenerated), both updated and checked by
`tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s running tag
count updated **634 -> 635 / 277 -> 278 `SF`** (`G191_165_48` probes cleanly
at the dictionary's 600-bar synthetic frame and takes many distinct values,
so the generator tags it `SF`). `tests/test_altport2_ports.py`'s
`CATEGORY_TOTAL` updated to match (289 -> 290); no `CATEGORY_BUCKETS` entry
needed (that dict only tracks `trend`/`volatility`/`volume`, not
`statistics`).

`g191_165`'s ledger row is now recorded (closed by this receipt session,
after the launcher's Gate E run). `mtd_ret` is still owed in the same
assertion, pre-existing and unrelated to this port (carried over from issue
#206, per `docs/G191076Measured.md`'s identical note).

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order (receipt
session, after the Gate E ledger row was recorded): **3 failed, 4591
passed, 83 skipped**. `g191_165`'s own tests (`tests/test_g191_165.py`):
**16 passed**. Pre-existing failures, all unrelated to this port (CLAUDE.md
"Known breaks" plus the owed Gate E row):
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
(owed for `['mtd_ret']` only -- `g191_165`'s row is now recorded, closing
its own owed entry; `mtd_ret` pre-dates this session),
`tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this worktree)
and `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
(untracked `docs/pine/` corpus). No other test regresses.
