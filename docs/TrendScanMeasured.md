# Trailing Trend Scan — measured (`trend_scan`)

Max-|t| trailing trend scan across a set of horizons: for each horizon `L`, the t-statistic
of the OLS slope of log price on time over the trailing `L` bars; emits the signed t of the
`L` with the largest `|t|`, and that `L` itself. Found by the ResearchIntel RAG scan of
2026-10-22, round 2. Source: Lopez de Prado, *Machine Learning for Asset Managers* (2020),
ch. 5 "Financial Labels" (6 hits, sim 0.78-0.84) — "trend scanning", described there as a
FORWARD-looking labelling method; this port keeps only the trailing, feature-side half.

**Status: Gates A, B, D cleared; Gate C synthetic only (real-data counts owed, no access
to the parent repo in this worktree); Gate E PENDING, run by the issue-solver launcher
after this session.** `trend_scan` is in `Category`, following the `pfe` / `kalman_trend` /
`ffd` precedent of registering before Gate E records (`docs/MLCompanionContract.md`).
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` fails until
the launcher's run is recorded with `docs/gate_e_ledger.py record`; that is expected, not a
bug in this session's work.

Shipped: `pandas_ta/statistics/trend_scan.py`, two columns `TSCAN_T_<horizons>` (signed
t-stat, SF) and `TSCAN_L_<horizons>` (the winning horizon, ORD), default
`_5-10-20-40-60`. Tests: `tests/test_trend_scan.py` (32). Every number below is printed by
`python docs/measure_trend_scan_proxy.py`, except the suite counts in Gate F. Environment:
pandas 2.3.3, numpy 2.5.4, Python 3.12. Measured 2026-10-31.

## Decisions the issue left open

**The horizon set was not specified ("The horizon set" was left as a bare line item in the
issue).** No owner or user was reachable to ask (headless session). **ASSUMPTION**: the
port's own choice, `(5, 10, 20, 40, 60)` — five trailing windows, short to medium daily-bar
lookbacks, the same order of magnitude as this repo's other multi-week params (`ADX` 14,
`KPSS`/`CUSUM` 100). A caller who wants a different set passes `horizons=`.

## The two decisions the task flagged

**🔴 Look-ahead trap.** The book uses trend scanning forward-looking, as a label. This port
reads bars `T - L + 1 .. T` only (trailing), never `T .. T + L - 1`. The Gate B mutant is
the task's explicitly-requested forward version: writing the SAME trailing-window
regression at the bar the window STARTS at, instead of the bar it ENDS at — which is
mathematically identical to the book's own forward form (`window [g, g+L-1]` "known" at `g`
is exactly `window [T-L+1, T]` "known" at `T-L+1`, with `g = T-L+1`). Measured by
future-perturbation (rewrite every bar from `j` onward, demand bars `[0:j]` bit-identical),
8 offsets past the warm-up, on a 4,000-bar synthetic walk:

    real module        leaks at  0/8 offsets
    forward mutant      leaks at  8/8 offsets

**🔴 Gate D — `log(8 * P)` is not guaranteed bit-identical to `log(P) + log(8)`.** Measured
directly, single horizon (`L=20`), 3,000-bar walk (seed 11, tick 0.05), max `|diff|` in the
t-stat under a power-of-two rescale:

    regressing on log(close) directly:        x8  4.170e-08    x64  1.601e-08
    regressing on log(close / anchor):        x8  0.000e+00    x64  0.000e+00

Chosen fix — a ratio, `z = log(close / anchor)` with `anchor` the series' first finite
positive close (the device `ffd` and `kalman_trend` use): computed by float DIVISION
before `log` is ever called, so under a power-of-two rescale the division cancels the
exact common factor and `z` is bit-identical by construction, not merely close.

The task's own phrasing anchors `P_ref` "inside the window" (re-picked per window). This
port uses ONE anchor for the whole series instead, because OLS slope/SE/t are invariant to
ANY additive shift of `z` — a window-local anchor and a series-wide anchor give the
IDENTICAL `(slope, t)` in exact arithmetic. Measured, `L=20`, three window positions on a
4,000-bar walk (seed 7), series-wide anchor vs a FRESH per-window ratio of raw prices
(`log(close / close[window start])`, recomputed from the raw series for each window, not
derived from the already-logged series-wide `z`):

    t_end=500:   series-wide -10.9235572394   window-local -10.9235572394   |diff| 2.132e-14
    t_end=1500:  series-wide   0.1509868109   window-local   0.1509868109   |diff| 5.829e-16
    t_end=3999:  series-wide   2.8260635330   window-local   2.8260635330   |diff| 7.105e-15

A series-wide anchor is what lets the module reuse ONE `z` across every horizon's rolling
sums (O(n) per horizon) instead of recomputing a fresh ratio inside every window (O(n * L)
per horizon) — the cost budget the issue asked for ("O(n·|L|) with rolling sums").

## A design decision this port made and reverted once

**The first implementation of the O(n)-per-horizon rolling sums used prefix sums weighted
by each bar's GLOBAL index** (`sum(g * z)` via `cumsum`, differenced between window
bounds). A review round caught this losing precision at long series lengths — subtracting
two `~n**2`-scale cumulative sums to recover an `O(length)`-scale window total. Measured
against a plain definitional-OLS oracle (sample means/covariances, not prefix sums), a
4,000-bar walk (seed 3), length 3:

                     global-index prefix sums        local recurrence (shipped)
    t_end=999 :      2.208e-09                       1.733e-10
    t_end=2500:      5.071e-08                       1.607e-09
    t_end=3999:      1.408e-06                        7.195e-08

The shipped version keeps three running sums bounded by the window instead — true
incremental rolling sums, updated by dropping the leaving bar and adding the entering one
each step (`S1 = sum(z)`, `S2 = sum(i*z)` with LOCAL `i`, `S3 = sum(z**2)`) — roughly 20x
more precise at every measured point, same O(n) cost per horizon, same algorithm the issue
asked for ("rolling sums"), just kept at the right numerical scale.

## Design decisions

| decision | why |
|---|---|
| horizons default `(5, 10, 20, 40, 60)` | ASSUMPTION — the issue did not specify a set; this port's own choice (see above) |
| trailing windows only, never forward | the task's 🔴; the book's own form is forward-looking, a label, not a feature |
| `z = log(close / anchor)`, series-wide anchor | bit-identical x8/x64 by construction, and reusable across every horizon's O(n) rolling sums (vs O(n\*L) for a window-local ratio) |
| local-recurrence rolling sums, not global-index prefix sums | ~20x more precise (measured above); same O(n) cost |
| a window with a NaN, zero or negative close is NaN for that horizon | the state is not poisoned; propagates through the window rather than being silently skipped |
| a degenerate (near-zero residual) fit is NaN, not inf | consistent with `kpss`/`cusum`'s "flat window has no variance; NaN not inf" |
| ties between horizons keep the smaller `L` | deterministic, simplest rule; strict `>` comparison when scanning horizons in ascending order |

## Gates

| gate | status |
|---|---|
| A Correctness | matches TWO independent oracles at 15 (horizon, bar) pairs: a plain definitional OLS (sample means/covariances, not the module's rolling-sum formulas) and the task's own cited identity `t = r * sqrt((n-2)/(1-r**2))`, both to 1e-6 (the formula's own floating-point floor at `length=3`, measured above; see "A design decision this port made and reverted once") |
| B Causality | future-perturbation, 8 offsets: real module 0/8 leaks; forward mutant (writes the same regression at the window's start bar instead of its end bar — the task's requested forward form) 8/8 leaks |
| C Reachability | **synthetic only**: 3,000-bar GBM, seed 11, tick 0.05, drift 0.0005, default horizons: 2,996 / 3,000 finite (warm-up 4 = min horizon 5, minus 1), 2,996 distinct T values, all 5 horizons used as the argmax somewhere (counts: L=5: 151, L=10: 248, L=20: 546, L=40: 706, L=60: 1,345). Real-data counts owed |
| D Scale-free | x8, x64: T max\|diff\| 0.0, bit-identical (`Series.equals` True); L max\|diff\| 0.0 both scales. x10, x3.7: T max\|diff\| 4.523e-08 / 8.271e-08 (test bound 1e-6), L max\|diff\| 0.0, NaN masks match; `0 < 2996 < 3000` fires, > 100 distinct T values |
| E Attribution | **PENDING**, run by the issue-solver launcher after this session. Proxy overlap below is NOT Gate E |
| F Suites | this repo: see the commit this file ships with; both repos' suites are run by the launcher in clean worktrees, per this session's rules |

## Proxy overlap (NOT Gate E) — disclosed, not ship-decided

Spearman ρ on one synthetic GBM walk (σ = 0.02, drift 0.0003, seed 1), n = 4,996, default
horizons:

| comparator | ρ |
|---|---|
| 100·(close / EMA₅ − 1) | 0.2471 |
| 100·(close / EMA₁₀ − 1) | 0.4070 |
| 100·(close / EMA₂₀ − 1) | 0.6184 |
| `BIAS_SMA_26` | 0.6347 |
| `ROC_5` | 0.2688 |
| `ROC_10` | 0.4354 |
| `ROC_20` | 0.6737 |
| `SLOPE_10` | 0.4097 |
| `SLOPE_40` | **0.8187** |
| `ADX_14` | 0.0663 |
| `CMO_14` / `RSI_14` | 0.7222 |
| `TRIX_30_9` | 0.7315 |
| `CUSUM_100` | 0.6483 |
| `KPSS_100` | 0.0232 |

**⚠ The maximum, `SLOPE_40` at 0.8187, is ABOVE this repo's 0.76 SHIP line and inside the
0.80-0.90 `DISCLOSE_GAP` band on this proxy.** It is not stable with volatility either —
σ from 0.005 to 0.05 moves it from 0.8375 down to 0.7762, still `SLOPE_40` at every point
tested:

    sigma=0.005: 0.8375   sigma=0.01: 0.8320   sigma=0.02: 0.8187   sigma=0.05: 0.7762

This is a plausible result, not a surprising one: `trend_scan`'s max-horizon case (`L=60`)
and `slope`'s own `L=40` are both "the slope of a linear fit over the last few dozen bars",
and t-stat and slope agree in sign and move together on a trending synthetic walk. This is
a synthetic proxy on comparators this repo already ships, on ONE seed family, not Gate E's
687-comparator sweep against the production engine's real columns on 89 BIST frames — but
it is a real signal that `trend_scan` may sit close to or above the ship line once real
data is in, closer than `ffd`'s proxy ceiling (0.7346) or most other recent ports. Gate E
decides; this section exists so that decision is not a surprise.

## To close

1. The issue-solver launcher runs Gate E (`gate_e_overlap.py build` then `run --module
   pandas_ta.statistics.trend_scan --name trend_scan`) against the parent repo's
   `compute_all` ∪ `ml_features` manifest, over the 89 ALTPORT-1 frames.
2. Record the run: `python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD`,
   then fill Gate C's real-data counts from the same frames and enter the Gate E verdict
   and max \|ρ\| above.
3. Apply CLAUDE.md's `r3-perframe-0.90` bands. Given the proxy's `DISCLOSE_GAP`-band
   ceiling against `SLOPE_40`, the owner should weigh whether `TSCAN_T` survives as
   written, or whether `SLOPE_40` (or a similarly-shaped existing column) already covers
   the question it answers. If STRUCK with no waiver, or if the owner judges the proxy
   ceiling too close to ship regardless: delete the module, the export, the `Category`
   entry, the accessor, the tests, the README counts, the dictionary row and the
   `MLCompanionContract` count, and keep this file. A revert closes the task as well as a
   ship.
4. Run both suites.
