# Volatility of Volatility — measured (`volvol`)

**Status: SHIPPED 2026-10-31. Gates A-E cleared below. F: run by the launcher in clean worktrees
of both repos.**

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
| C Reachability | Synthetic (seed-11 walk, 1,200 bars): 1,168 of 1,200 bars finite (32-bar warm-up: 13 leading-NaN bars before the inner `natr` EMA seeds + 19 more valid `natr` bars to fill the outer 20-bar rolling stdev window), all 1,168 non-zero, range [0.091438, 0.566766], mean 0.241904. Real data (Gate E run, 89 ALTPORT-1 BIST frames, 398,849 pooled bars): 396,001 non-NaN, 391,032 non-zero. |
| D Scale-free | ×8 and ×64 bit-identical with matching NaN masks — `natr` is already a price ratio that is exact under a power-of-two rescale in IEEE float (the `100/close` and `ATR` scale factors cancel bit-exactly), and a rolling sample stdev of an exactly-scaled series is itself exactly scaled (sum, mean, and the final `sqrt` of an exact `k²`-scaled variance all stay exact under IEEE 754 for a power-of-two `k`). ×10 and ×3.7 within 3.081e-14 / 2.132e-14 (well under CLAUDE.md's 1e-12 bar). `0 < fires < n` (1,168 of 1,200) plus >100 distinct values and a non-constant column (`test_column_is_not_constant`), so a degenerate pass cannot sneak through. |
| E Attribution | **Measured 2026-10-31**, `gate_e_overlap.py run --module pandas_ta.volatility.volvol` (Backtesting #107), 89 ALTPORT-1 BIST frames, 687 comparators (329 `compute_all` + 358 manifest `1d`), n=396,001 pooled bars. `VOLVOL_20_14`: pooled max\|ρ\| **0.6408** against `natr` (also the top `compute_all` hit); manifest-side max\|ρ\| 0.6408 against `Stop_2ATR_pct`. Per-frame median\|ρ\| 0.6190 against `natr` (max across comparators), 0 of 89 frames ≥ 0.90. Confirms the issue's guess that this is a second-order function of `natr`, but the correlation is far below the ship line. Band (`r3-perframe-0.90`): pooled 0.6408 < 0.76 and per-frame max-median 0.6190 < 0.90 → **SHIP**. |
| F Suites | Run by the launcher in clean worktrees of both repos. |

### Suite runs

Build session (`python -m pytest -q`, this worktree, not a clean checkout): the new
`tests/test_volvol.py` (11 tests) passed in isolation; 142 passed alongside the one expected
`tests/test_gate_e_ledger.py` failure (no ledger row yet).

Receipt session (after `docs/gate_e_ledger.py record`, this worktree): full suite run, see below.

## Closed

Gate E ran SHIP (0.6408 < 0.76, no per-frame ≥ 0.90). Ledger row recorded
(`docs/gate_e_ledger.py record ... --measured 2026-10-31`). `volvol` stays in `Category`, wired
as built — nothing reverted. Gate F is the launcher's clean-worktree run of both repos' suites.
