# Connors RSI — measured (`crsi`)

Connors Research's composite momentum oscillator (Kaufman 2013, ch. 9 "Momentum and
Oscillators"): `(RSI(close, 3) + RSI(streak, 2) + PercentRank(1-bar return, 100)) / 3`, where
`streak` is the signed count of consecutive up or down closes. Found by the ResearchIntel RAG
scan of 2026-10-22, round 2 (report `PandasTaIndicatorCandidates-2026-10-22.md`, 5 hits).
Kaufman 2013 was not available on this machine, so nothing below is checked against it line
by line; the formula is the one quoted in the issue, independently re-derived in
`tests/test_crsi.py::test_matches_an_independent_loop`.

**Status: Gates A, B, D cleared; Gate C synthetic only (real-data counts owed); Gate E
PENDING, run by issue-solver after this session. Do not merge to `main` before Gate E**:
`crsi` is in `Category`, so any `df.ta.strategy()` sweep in the parent repo picks it up, as
`pfe`/`kalman_trend` were under the same deferral precedent (`docs/PfeMeasured.md`,
`docs/KalmanTrendMeasured.md`).

Shipped: `pandas_ta/momentum/crsi.py`, three columns — `CRSI_3_2_100` (the composite),
`CRSI_STREAK_2`, `CRSI_PCTRANK_100` — all bounded `[0, 100]`. Tests: `tests/test_crsi.py`
(14). Numbers: `python docs/measure_crsi_proxy.py`. Environment: pandas 2.3.3, numpy 1.26.4,
Python 3.11.2. Measured 2026-10-31.

## What is NOT shipped, and why

`RSI(close, 3)` is computed internally for the composite but is **not** its own output
column. At the default `rsi_length=3` it is exactly `ta.rsi(close, 3)`, already available
from the shipped `rsi` indicator — shipping it again would be a redundant column
(CLAUDE.md's non-redundant rule). This confirms the issue's guess ("the RSI(3) term
probably restates `rsi`") without needing Gate E: it is a literal restatement, not a
correlation.

The composite and both components ship together, pending Gate E, rather than picking one
of "composite / components / streak only" up front — the issue says to let Gate E settle
that, and Gate E has not run yet in this session.

## Design decisions

| decision | why |
|---|---|
| `streak[0] = 0`, and 0 on any unchanged close | there is no prior close to compare the first bar against; an exact tie breaks a run rather than extending it either direction |
| `RSI(streak, streak_length)` reuses the shipped `rsi()` formula verbatim on the streak series, not a different smoothing | Connors' definition feeds the streak through an ordinary Wilder RSI; a bespoke smoothing would not be "RSI of the streak" |
| `PercentRank(x, n)` = Pine's `ta.percentrank`: 100 × (count of the PREVIOUS `n` values strictly less than the current one) / `n` | ties do not count — the only percent-rank convention with a citable public formula available on this machine |
| `1-bar return` = `close.pct_change(1)` | rank order is invariant under the monotonic transform between simple and log return, so the choice does not change any `PercentRank` output |

## Causality

Future-perturbation over 28 offsets (150 to 1085, step 35, past the 101-bar warm-up):
**real module 0 leaks**. Two look-ahead mutants (`importlib` source read, one line
replaced, `exec`'d in memory), each proved live then **caught at 28 of 28**:

* `streak_future` — the streak's direction read 10 bars ahead (`close.shift(-10) - close`
  instead of `close.diff()`).
* `pctrank_centered` — the percent-rank window centered (`rolling(..., center=True)`
  instead of trailing), the same `centered=True` bug class CLAUDE.md flags for `dpo`.

The perturbation itself had to be redesigned mid-port: splicing in an unrelated random
walk's tail (the `pfe`/`kalman_trend` precedent) makes a future *sign* read's detection
rate depend on the two walks' relative level at that specific bar index, which drifts over
a long GBM path and is NOT close to the expected 50/50 per offset — observed well short of
28/28 across several attempts during development (informal, not reproducible from a
committed script, unlike every other number in this file). Shifting the SAME series
by a huge constant (±1e6) instead, and counting a leak if EITHER direction shows a
difference, closed the gap to 28/28: a forced-positive read can coincide with a bar that
was already locally trending up (and so go undetected on its own), but the forced-negative
read then cannot also coincide.

## Gates

| gate | result | evidence |
|---|---|---|
| A Correctness | self-consistency (no page-citable source on this machine) | matches an independent loop (Wilder RSI via plain `ewm`, streak and percent rank via plain Python loops, none calling `pandas_ta.momentum.rsi` or the module's own helpers) to 1e-9 on a 400-bar walk; two hand-computed examples: streak `[0, 1, 2, -1, -2, -3, 1]` for closes `10,11,12,11,10,9,10`, and `PercentRank([5,6,4,7], 3) = 100.0` (plus a 4-way tie reading 0, not 50) |
| B Causality | pass | 0 real leaks / 28 offsets; both mutants caught 28/28 (see above) |
| C Reachability | synthetic only | 1,200-bar tick-rounded walk (seed 11, tick 0.05): `CRSI_3_2_100` 1,099 finite / 1,099 nonzero / 541 below 50 / 558 above 50 / 1,099 distinct values; `CRSI_STREAK_2` 1,198 finite / 1,198 nonzero / 583 below 50 / 615 above 50; `CRSI_PCTRANK_100` 1,099 finite / 1,085 nonzero / 547 below 50 / 540 above 50 / 101 distinct values. **Real-data counts owed.** |
| D Scale-free | pass | ×8 / ×64 bit-identical (max diff 0.0 for all 3 columns, matching NaN masks); ×10 / ×3.7 within 1e-9 (measured 1.563e-13 / 1.208e-13); every column `0 < fires < n` with > 100 distinct values |
| E Attribution | **PENDING** — run by issue-solver after this session | `gate_e_overlap.py run --module pandas_ta.momentum.crsi --name crsi` against `compute_all` ∪ the `ml_features` manifest `1d`, 89 ALTPORT-1 BIST frames, bands `r3-perframe-0.90` |
| F Suites | this repo only | 3,822 passed / 83 skipped / 3 failed (2026-10-31). All 3 failures are pre-existing and unrelated to this port: `test_pine_coverage_csv::test_audited_rows_carry_their_evidence` (CLAUDE.md's known break), `test_altrepo_talib_csv::test_regenerating_reproduces_the_committed_rows` (needs the sibling `../AlternativeRepos` checkout, not present), and `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (expected: `crsi` has no ledger row until Gate E runs and records one). Parent repo run by the launcher, not in this session. |

## Proxy overlap (NOT Gate E)

Spearman ρ against this package's own `[0, 100]`-bounded oscillators, one synthetic GBM
walk (σ = 0.02, seed 1), n = 2,899:

| comparator | `CRSI_3_2_100` | `CRSI_STREAK_2` | `CRSI_PCTRANK_100` |
|---|---|---|---|
| `ROC_1` | **0.9214** | 0.7461 | **0.9898** |
| `RSI_3` | 0.8485 | 0.5846 | 0.6534 |
| `WILLR_14` | 0.6497 | 0.3684 | 0.4634 |
| `ROC_5` | 0.5968 | 0.2989 | 0.4023 |
| `RSI_14` / `CMO_14` | 0.4646 | 0.2217 | 0.2852 |
| `STOCHRSIk_14_14_3_3` | 0.3880 | 0.1326 | 0.1917 |

Within-indicator: composite vs `CRSI_STREAK_2` ρ 0.8685, composite vs `CRSI_PCTRANK_100` ρ
0.9119, `CRSI_STREAK_2` vs `CRSI_PCTRANK_100` ρ 0.7394 (expected — the composite is their
average, by construction, not evidence of redundancy with a *different* shipped signal).

`CRSI_PCTRANK_100` sits very close to a rank-transform of `ROC_1` (ρ 0.9898) — expected,
since `PercentRank(x, n)` is a monotonic transform of `x`, and a strong signal that it may
be redundant with a 1-bar-return feature if one is in the production comparator set.
`CRSI_STREAK_2` is comparatively the most novel of the three on this proxy (max 0.7461,
against `ROC_1`), matching the issue's hypothesis that "the streak RSI... [is] the new
part" — but this proxy only covers this package's own momentum oscillators, not the
engine's 687-comparator set; Gate E, not this table, decides.

## To close

1. In the parent repo, run `gate_e_overlap.py run --module pandas_ta.momentum.crsi --name
   crsi`, and enter the maximum `|ρ|` per column, its comparator and its sample size above.
2. Record the run: `python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD`.
3. Fill Gate C from the same real frames.
4. Apply CLAUDE.md's `r3-perframe-0.90` thresholds per column. Delete any column at or
   above the revert line. If that leaves no columns standing, delete the whole module,
   its export, `Category` entry, accessor, tests, README counts, dictionary row and
   `MLCompanionContract` count — a revert closes this issue as well as a ship.
5. Run both repos' suites.
