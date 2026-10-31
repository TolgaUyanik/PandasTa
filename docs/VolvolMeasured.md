# Volatility of Volatility — measured (`volvol`)

**Status: BUILT 2026-10-31. Gates A, B, C, D cleared below (this session). Gate E: pending, run
by issue-solver after this session. F: run by the launcher in clean worktrees of both repos.**

Column `VOLVOL_20_14`: the rolling 20-bar standard deviation of a rolling 14-bar `natr` series —
vol-of-vol, the instability of an asset's own volatility estimate. Category `volatility`.

## Source

Alpha Architect, "Volatility Anomalies: IVOL and Vol-of-Vol"; Kaufman, Perry J. (2013), *Trading
Systems and Methods*, 5th ed., ch. 18 ("Volatility Measurements and Position Sizing") — both
describe vol-of-vol as the standard deviation of a rolling volatility estimator taken over a
further rolling window; neither is a Pine source, so Gate A is checked against an independent
loop written from the formula text (below), not against a cited source line — the same situation
as `tf_median_absdiff_20` against TSFEL and `pfe` against Hannula's published formula. IVOL itself
needs a benchmark regression (same treatment as `beta`) and is explicitly out of scope per the
issue.

**Design choice — stdev, not coefficient of variation.** The issue allows either form ("rolling
stdev (or coefficient of variation) of a rolling volatility series"). This port ships the plain
stdev: the inner volatility series is `natr` (`100 * ATR / close`), which is already scale-free
(a price ratio, not a price level), so stdev of it is scale-free too without needing a division —
a CV form (`stdev(natr) / mean(natr)`) would read `0/0 = NaN` on a window where `natr`'s mean is
exactly 0, which `natr` itself cannot produce on real price data (true range is 0 only on an
exact-flat bar) but is reachable on degenerate synthetic input. Stdev has no such failure mode.

**Overlap, per the issue:** guessed (not measured until Gate E runs) to be a second-order function
of `natr`, since it is literally built on `natr`.

## Calculation

```
NATR     = natr(high, low, close, length=natr_length)      # 100/close * ATR, mamode='ema'
VOLVOL   = NATR.rolling(length).std()                       # trailing sample stdev, ddof=1
```

Default `length=20`, `natr_length=14`. `mamode` forwards to the inner `natr` call (default
`'ema'`, matching `natr`'s own default).

## Gates

Environment: Python 3.11.2, pandas 2.3.3, numpy 1.26.4 (`python docs/measure_volvol.py`).
Synthetic numbers are a 1,200-bar GBM walk, σ = 0.02, seed 11, 0.05 tick, high/low built as
`close ± |N(0, σ/4)| * close`, the same OHLC `tests/test_volvol.py` uses.

| Gate | Result |
|---|---|
| A Correctness | Checked against an independent loop (`tests/test_volvol.py::test_matches_an_independent_natr_plus_stdev_loop`) that re-derives true range, an SMA-seeded EMA (`span=natr_length`, `adjust=False` — matching `pandas_ta.overlap.ema`'s SMA seed, NOT Wilder's `alpha=1/length`), the `100/close` scale factor, and a rolling stdev — all written from the formula text, not by importing `natr`/`volvol`. Max\|diff\| < 1e-9 over 400 bars (>300 compared bars after the 32-bar double warm-up). No published source line is cited (neither source is a Pine file; see Source). |
| B Causality | 30-offset future-perturbation sweep on OHLC (`test_real_module_never_reads_the_future`): the real module leaks at 0 of 30 offsets. The catching mutant shifts the inner `natr` series 10 bars into the future (`importlib`-read source, `exec`'d in memory with `__package__` set so the module's own `from .natr import natr` resolves) and is caught at 30 of 30 (`test_mutant_is_caught`). |
| C Reachability | Synthetic (seed-11 walk, 1,200 bars): 1,168 of 1,200 bars finite (32-bar warm-up: 13 leading-NaN bars before the inner `natr` EMA seeds + 19 more valid `natr` bars to fill the outer 20-bar rolling stdev window), all 1,168 non-zero, range [0.091438, 0.566766], mean 0.241904. Real-data counts come from the Gate E run (pending). |
| D Scale-free | ×8 and ×64 bit-identical with matching NaN masks — `natr` is already a price ratio that is exact under a power-of-two rescale in IEEE float (the `100/close` and `ATR` scale factors cancel bit-exactly), and a rolling sample stdev of an exactly-scaled series is itself exactly scaled (sum, mean, and the final `sqrt` of an exact `k²`-scaled variance all stay exact under IEEE 754 for a power-of-two `k`). ×10 and ×3.7 within 3.081e-14 / 2.132e-14 (well under CLAUDE.md's 1e-12 bar). `0 < fires < n` (1,168 of 1,200) plus >100 distinct values and a non-constant column (`test_column_is_not_constant`), so a degenerate pass cannot sneak through. |
| E Attribution | **Pending, run by issue-solver after this session.** Guessed (not measured) in the issue to land against `natr` / `natr_percentile`, since `VOLVOL` is a second-order function of `natr`. |
| F Suites | Run by the launcher in clean worktrees of both repos. |

### This session's own suite run

`python -m pytest -q` (this worktree, not a clean checkout): the new `tests/test_volvol.py`
(11 tests) passes in isolation. `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails — expected: `volvol` is wired into `Category` per this issue's rules, and that specific test
stays red until a later session records its Gate E ledger row. No other test in
`tests/test_gate_e_ledger.py` regresses (142 passed alongside that one expected failure, checked
in this worktree before commit). The full-suite count and whether any other module regresses is
for the launcher's clean-worktree run (Gate F), not asserted here.

## To close

1. Gate E: launcher runs `gate_e_overlap.py run --module pandas_ta.volatility.volvol`.
2. Record the run: `python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD`.
3. Fill in the Gate E row above with the measured max \|ρ\|, its comparator, and the SHIP /
   DISCLOSE / DISCLOSE_GAP / STRUCK band.
4. If STRUCK: this module, its wiring, and its tests are reverted; this file stays as the receipt
   per the issue's "measured and reverted" closing condition.
5. If SHIP / DISCLOSE / DISCLOSE_GAP: nothing further to wire — `volvol` is already in `Category`
   (not withheld, per this issue's rules) — just fill in Gate C's real-data counts from the same
   run and confirm both suites (Gate F).
