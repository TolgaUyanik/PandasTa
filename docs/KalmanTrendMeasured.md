# Kalman local-linear-trend filter — measured (`kalman_trend`)

A two-state (level, velocity) Kalman filter on log price. It emits the close's percent
distance from the filtered level (`KFT_DIST`) and the filtered velocity in log-percent per
bar (`KFT_VEL`). Found by the ResearchIntel RAG scan of 2026-10-22, round 2. Sources: Alpha
Architect, *Trend-Following Filters* Parts 4–5; Chan (2013) ch. 3. Neither source was
available on this machine, so nothing below is checked against them line by line. The
recursion is the textbook predict/update.

**Status: Gates A, B, D cleared; Gate C synthetic only (real-data counts owed); Gate E
DEFERRED by this repo's owner on 2026-10-23 (the parent repo is not theirs and not on this
machine) — deferred, not passed; verdict pending. Do not merge to `main` before Gates C (real-data counts) and E**:
`kalman_trend` is in `Category`, as `pfe` was under the same deferral
(`docs/PfeMeasured.md`), so any `df.ta.strategy()` sweep in the parent repo picks it up.
Registering it before Gate E follows that precedent and is the owner's call. On the proxy
below, **both columns sit in the band CLAUDE.md leaves undefined (0.80 to ≈ 0.9)**:
`KFT_VEL` measures 0.8992 against PPO on the synthetic proxy, at the ≈ 0.9 revert line.
Gate E decides.

Shipped: `pandas_ta/overlap/kalman_trend.py`, two columns `KFT_DIST_<q_level>_<q_slope>`
and `KFT_VEL_<q_level>_<q_slope>` (default `_0.01_0.0001`; the `q_*` are formatted with
`.12g`, so 1e-05 names as `1e-05`, 0.0 as `0`, and 0.01000001 does not collapse to `0.01`;
negative or non-finite `q_*` raise `ValueError`, and so does any pair whose Riccati recursion
needs more than 5000 steps: `q_slope` small relative to `q_level`, roughly a warm-up beyond
~5000 updates, e.g. (0.01, 1e-8), (2, 1e-5), (30, 1e-4)). Tests: `tests/test_kalman_trend.py` (32).
**Every number below is printed by `python docs/measure_kalman_trend_proxy.py`**, except the
suite counts in Gate F. Environment: pandas 2.3.3, numpy 2.5.4, Python 3.12 (`.venv-pd2`).
Measured 2026-10-23.

## Design decisions

| decision | why |
|---|---|
| state on y = ln(close / first positive close) | a price ratio is exact under a power of two, so ×8/×64 is bit-identical; the anchor cancels out of both columns |
| noise variances fixed (`q_level=0.01`, `q_slope=0.0001`, ratios to a measurement noise of 1) | fitting by maximum likelihood on the full series is a look-ahead (a mutant doing exactly that is caught, Gate B). A trailing-window fit was not built: see below |
| diffuse prior, P₀ = 10⁴·I, state (0, 0) | the start is forgotten at the rate measured under *Warm-up* |
| a NaN, zero or negative close: predict only, emit NaN | the state is not poisoned; tested for all three |

With fixed variances the Kalman gain does not depend on the data. It converges to
(0.1590, 0.0092) for (level, slope), and after the warm-up the filter is a fixed linear
filter on log price, of the Holt (level + trend exponential smoothing) type. This is the
structural reason for the overlap below. A trailing-window ML fit of the variances would
make the gain data-dependent, which is the only thing that could make it novel. It was not
built, because Gate E has not yet ruled on the fixed form.

## Warm-up (the head, not only the tail)

The start-up transient decays at the steady-state closed-loop spectral radius ρ. The
warm-up is `ceil(ln 1e-8 / ln ρ)` **updates** (valid closes, not bars: a predict-only bar
does not shrink the transient). It is computed from the parameters by iterating the
Riccati recursion, which never reads data, so the NaN mask cannot leak the future. A fixed
default would be wrong for any other `q_*`. Why 1e-8: the unmasked transient measures 16.1
at its first bar; the measured head worst left is 4.0e-7 at the defaults (decay runs slower
than ρ predicts: 120 vs 112 bars to 1e-3, below), under the 1e-6 the head test asserts.

Head check: filter started at bar s ∈ {100, 500, 900} vs bar 0, worst |diff| from the
FIRST emitted bar on, 10 seeds × σ ∈ {0.005, 0.02, 0.05} (90 runs per row):

| (q_level, q_slope) | steady gain (level, slope) | ρ | warm-up | head worst |
|---|---|---|---|---|
| (0.01, 0.0001) default | (0.1590, 0.0092) | 0.9170 | 213 | 4.0e-7 |
| (0.0, 0.001) | (0.2226, 0.0279) | 0.8817 | 147 | 2.5e-7 |
| (0.1, 0.001) | (0.3316, 0.0259) | 0.8993 | 174 | 1.5e-7 |

The warm-up grows fast as `q_slope` shrinks: (0.1, 1e-5) needs 1,842 and (0.01, 1e-5) needs
549.

At the defaults, on the same 90 runs with the mask removed:

| check | measured |
|---|---|
| worst \|diff\| at the first bar | 16.1 |
| first bar after which it stays under 1e-3, vs `ceil(ln(1e-3/16.1) / ln ρ)` | 120 vs 112 |
| emitting from W // 2 = 106 instead (seed 3, s = 500), \|diff\| on `KFT_DIST` at the first emitted bar | 1.6e-3 |

The last row is the Hilbert lesson in CLAUDE.md: a shorter warm-up would pass any check
run on the tail and still emit a start-dependent value at the head.

## Gates

| gate | status |
|---|---|
| A Correctness | matches an independent matrix-form filter (F, H, Q, R, P from the textbook equations, with its own predict-only branch) to 1e-9 on 900 bars that include a NaN close and a zero close; a log-linear series reads DIST → 0, VEL → its step (0.3 %/bar) to 1e-6. Leading NaNs only shift the output (bit-identical); an all-NaN series, or one with ≤ warm-up valid closes, returns None |
| B Causality | future-perturbation over 32 offsets past the warm-up: real module 0 leaks. Four mutants, each proved live, then caught at 32 of 32: observation read `y[t+1]`, `dist` write back-dated, `vel` write back-dated, and `q_slope` scaled by the variance of the WHOLE series (the full-series fit the task forbids; column names left unchanged, so the catch is on values, not names) |
| C Reachability | **synthetic only**: 1,200-bar GBM, seed 11, tick 0.05: 987 finite per column; DIST 491 pos / 496 neg, VEL 538 pos / 449 neg, 0 exact zeros. Real-data counts owed |
| D Scale-free | ×8, ×64 max diff 0 and `DataFrame.equals` in the test; ×10, ×3.7 max diff 2.8e-14 (test bound 1e-9), NaN masks match; both columns `0 < positive < n` with > 100 distinct values |
| E Attribution | **DEFERRED** by the owner, 2026-10-23: the parent repo is out of this repo's scope and not on this machine. Write `../Backtesting/scripts/analysis/measure_kalman_trend_overlap_full.py` against the engine's full production column set |
| F Suites | this repo, pandas 2.3.3: 2 failed / 3,159 passed / 85 skipped / 1 error (re-run 2026-10-23 after round 3; the error is `test_altrepo_talib_csv`'s `tmp_path` under a sandbox run with `-p no:tmpdir`, not a test failure). Both failures are pre-existing and unrelated: `test_pine_coverage_csv::test_audited_rows_carry_their_evidence` (the CLAUDE.md known break) and `test_wilder_rma::test_the_incumbents_did_not_move` (`natr` off by 1 ulp under numpy 2.5.4; fails identically with this port stashed). Parent repo not run |

## Proxy overlap (NOT Gate E)

Spearman ρ on one synthetic GBM walk (σ = 0.02, seed 1), n = 2,787:

| comparator | `KFT_DIST` | `KFT_VEL` |
|---|---|---|
| 100·(close / EMA₅ − 1) | **0.8644** | 0.2558 |
| 100·(close / EMA₁₀ − 1) | 0.8621 | 0.4674 |
| `ROC_5` | 0.8345 | 0.2816 |
| `PPO_12_26_9` | 0.0594 | **0.8992** |
| `ROC_20` | 0.3706 | 0.8528 |
| `CMO_14` / `RSI_14` | 0.5473 | 0.8230 |
| `BIAS_SMA_26` | 0.5907 | 0.7896 |
| `PFE_10_5` | 0.4870 | 0.6740 |
| `KFT_DIST` vs `KFT_VEL` | 0.0394 | |

The maxima do not move with volatility (σ from 0.005 to 0.05: DIST 0.8644–0.8645,
VEL 0.8991–0.8995), as expected of a fixed linear filter.

The task's pre-registered guess was that the level-distance column would die and the
velocity column was the more novel one. On the proxy it is **the other way round**: `KFT_VEL`
is the closer restatement (of PPO), at 0.8992. `KFT_DIST` is at 0.8644 against a 5-bar EMA
distance, which may not be in production. Whether PPO or a short EMA distance is in the
production set is unknown here. Gate E decides.

## To close

1. In the parent repo, write `measure_kalman_trend_overlap_full.py` from an existing
   `measure_*_overlap_full.py`, run it, and enter the maximum |ρ| per column, its comparator
   and its sample size above.
2. Fill Gate C from the same real frames.
3. Apply CLAUDE.md's thresholds per column. Delete a column that fails and keep the other.
   If both fail, delete the module, the export, the `Category` entry, the accessor, the
   tests, the README counts, the dictionary row and the `MLCompanionContract` count, and keep
   this file. A revert closes the task as well as a ship.
4. Run both suites.
