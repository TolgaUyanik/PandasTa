# AFML Fixed-Width Window Fractional Differencing — measured (`ffd`)

A rolling linear filter of log price that keeps more memory than a one-bar return (`FFD`),
AFML's canonical "make price ML-ready" transform. Found by the ResearchIntel RAG scan of
2026-10-22. Sources: Lopez de Prado, *Advances in Financial Machine Learning* (2018), ch. 5
"Fractionally Differentiated Features" (all 6 top hits); the book was not available on this
machine, so the recursion is implemented from the task's own description of AFML Snippets
5.1-5.2 (`getWeights_FFD`, `fracDiff_FFD`), not checked line-by-line against the printed
book.

**Status: Gates A, B, D, E cleared; Gate C synthetic only (real-data counts owed, no
access to the parent repo in this worktree).** Gate E ran 2026-10-31 (run
`is13-ffd-406bc97e`), verdict `DISCLOSE_GAP` (0.80 ≤ max |ρ| < 0.90, not STRUCK) — shipped,
disclosed below. Recorded in `docs/gate_e_ledger.csv` via `docs/gate_e_ledger.py record`.

Shipped: `pandas_ta/statistics/ffd.py`, one column `FFD_<d>_<threshold>` (default
`_0.4_0.0001`). Tests: `tests/test_ffd.py` (34). Every number below is printed by
`python docs/measure_ffd_proxy.py`, except the suite counts in Gate F. Environment:
pandas 2.3.3, numpy 2.5.4, Python 3.12. Measured 2026-10-31.

## The two decisions the task flagged

**🔴 Gate D — the truncated weights do not sum to zero.** AFML's `getWeights_FFD` truncates
the binomial-series weights of `(1 - x)^d` the moment `|w_k|` drops below `threshold`,
leaving a residual `s = sum(w_k)` that is a fixed, non-zero number for a given
`(d, threshold)`. Left uncorrected this breaks TWO things, not one:

1. `FFD(log(c * close)) = FFD(log close) + log(c) * s` is not scale-free.
2. Because a window's constant term never cancels, the filtered value depends on the
   log-price reference point used — and if that reference is the window's own first bar
   (the natural causal choice), the output depends on where the caller's series happens to
   start. **Measured directly, raw weights vs re-centred, at the IDENTICAL (d=0.4,
   threshold=1e-5, width 1,458)** — `docs/measure_ffd_proxy.py`'s "Gate D defect" block runs
   both weight vectors through the same experiment (slicing a 4,000-bar synthetic walk at
   bar 100/500/900, re-anchoring, comparing to the un-sliced run): the raw weights move the
   value by **1.3e-02 / 4.7e-02 / 6.3e-02**; the re-centred weights this module ships move it
   by **1.1e-15 / 1.3e-15 / 1.3e-15** — seven orders of magnitude smaller, and under this
   repo's 1e-9 head-stability bar.

Chosen fix — **a re-centred form**, one of the two options the task named: `_ffd_weights`
moves the whole residual `s` onto the most-lagged kept weight (the smallest in magnitude,
the minimal single-weight correction), forcing `sum(w) = 0` to float precision. This fixes
both failures: a constant added to the whole series now contributes `0 * constant` instead
of `s * constant`, so the anchor-dependence bug disappears and the series is a true
high-pass filter immune to a constant level. On top of this, the module still measures
`y = log(close / first finite positive close)` rather than raw log price — the same device
`kalman_trend` uses — because a power-of-two price rescale leaves that ratio bit-identical
by construction (correctly-rounded division cancels an exact common factor), making x8/x64
**exact** rather than merely small; re-centring alone would only bound it to the ~1e-15 noise
floor of evaluating `log` on two different numbers, which is still inside tolerance but not
exact. Both are measured below, at this module's actual default `threshold=1e-4`.

**🔴 Causality of `d`.** AFML's own worked example picks the smallest `d` whose FFD series
passes an ADF test on the FULL sample — a look-ahead. Chosen fix — the first option the
task named: `d` is a **FIXED parameter** the caller supplies (default 0.4; AFML's own
examples put the ADF-passing `d` for a daily equity/futures series in roughly the 0.3-0.5
range, cited from the task's description, not re-derived here — no ADF implementation was
built). It is never estimated from the series being transformed. A trailing-window
ADF-based picker was not built: CLAUDE.md asks for the narrowest change, and a causal `d`
selector is a second indicator's worth of machinery with its own warm-up and test suite.

## Design decisions

| decision | why |
|---|---|
| `d` fixed, never fit (default 0.4) | an ADF-on-full-sample `d` selector is a look-ahead (the task's 🔴); a trailing-window selector was not built (narrowest change) |
| weights re-centred so `sum(w) = 0` | the raw AFML weights' non-zero sum is anchor-dependent AND not scale-free; moving the residual onto the smallest weight fixes both with a one-line change |
| `y = log(close / anchor)`, `anchor` = first finite positive close | makes x8/x64 bit-identical by construction (same device as `kalman_trend`), on top of the re-centring |
| default `threshold=1e-4`, not AFML's 1e-5 | 1e-5 needs 1,458 bars just to emit a first value (almost 6 years of daily bars) and does not fit this repo's 600-bar live-probe frame; 1e-4 needs 282. A caller can still pass `threshold=1e-5` |
| a window with a NaN, zero or negative close is NaN | the state is not poisoned; propagates through the dot product rather than being silently skipped |

## Gates

| gate | status |
|---|---|
| A Correctness | weights (before the last one) match the closed-form generalised binomial coefficient `(-1)^k * C(d,k)` two ways, over 4 `(d, threshold)` pairs: a plain product loop (same formula as the module's recursion, independent code path — catches a sign/off-by-one coding bug, not a conceptual mismatch with AFML's own recipe, which this port could not check line-by-line against the printed book), and, for the first 40 weights where it cannot overflow, `math.gamma` directly (a genuinely different numerical codepath). Both to 1e-9. The re-centring is verified to force `sum(w) < 1e-9`; the full convolution matches an independently written plain-Python loop (not `sliding_window_view`) to 1e-9, including a NaN, a zero and a negative close in the window |
| B Causality | future-perturbation over 8 offsets past the warm-up: real module 0 leaks. Two mutants, each proved live, then caught at 8 of 8: the output write back-dated by one bar, and the anchor read from `usable[-1]` (the END of the series) instead of `usable[0]` — the look-ahead class the task's 🔴 flagged, here as a data-dependent reference rather than a fitted parameter, since `d` itself is never fit |
| C Reachability | **synthetic only**: 3,000-bar GBM, seed 11, tick 0.05, default `d, threshold`: 2,719 finite, 2,719 nonzero (1,629 pos / 1,090 neg), 2,719 distinct values. Real-data counts owed |
| D Scale-free | x8, x64 max diff 0.0 and `Series.equals` True; x10, x3.7 max diff 3.3e-16 / 4.4e-16 (test bound 1e-9), NaN masks match; `0 < 2719 < 3000` fires, > 100 distinct values |
| E Attribution | **DISCLOSE_GAP.** `FFD_0.4_0.0001` max \|ρ\| = 0.8494 vs `Dist_to_SMA_200_pct` (manifest, n = 373,840); per-frame max median \|ρ\| = 0.8425 (same comparator, 89 frames, 0.0% of frames ≥ 0.90 pooled-only). Run `is13-ffd-406bc97e`, 2026-10-31, 687 comparators (329 `compute_all` + 358 `ml_features` manifest), 89 ALTPORT-1 frames. Band: 0.80 ≤ ρ < 0.90, not STRUCK — shipped |
| F Suites | this repo: see the commit this file ships with; both repos' suites are run by the launcher in clean worktrees, per this session's rules |

## Proxy overlap (NOT Gate E)

Spearman ρ on one synthetic GBM walk (σ = 0.02, seed 1), n = 4,719, default `d, threshold`:

| comparator | ρ |
|---|---|
| 100·(close / EMA₅ − 1) | 0.5750 |
| 100·(close / EMA₁₀ − 1) | 0.6445 |
| 100·(close / EMA₂₀ − 1) | 0.7090 |
| `BIAS_SMA_26` | 0.6704 |
| `ROC_1` | 0.3960 |
| `ROC_5` | 0.5114 |
| `ROC_10` | 0.5602 |
| `ROC_20` | 0.6054 |
| `SLOPE_10` | 0.5328 |
| `PPO_12_26_9` | 0.4842 |
| `TRIX_30_9` | 0.6107 |
| `CMO_14` / `RSI_14` | **0.7346** |
| `CUSUM_100` | 0.7079 |
| `KPSS_100` | -0.0182 |

The maximum (CMO_14 / RSI_14, 0.7346) does not move much with volatility (σ from 0.005 to
0.05: 0.7345-0.7351), and sits comfortably under the 0.76 SHIP line — but this is a
synthetic proxy on comparators this repo already ships, not Gate E's 687-comparator sweep
against the production engine's real columns on 89 BIST frames. Gate E decides.

## Gate E close-out (2026-10-31)

Gate E ran against the production engine's `compute_all` ∪ `ml_features` manifest (687
comparators) over the 89 ALTPORT-1 BIST frames; outputs recorded in
`docs/gate_e_ledger.csv` (run `is13-ffd-406bc97e`).

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---|---|---|---|---|
| `FFD_0.4_0.0001` | 0.8494 | `Dist_to_SMA_200_pct` (manifest) | 373,840 | 0.8425 | `DISCLOSE_GAP` |

`DISCLOSE_GAP` (0.80 ≤ max \|ρ\| < 0.90) is not `STRUCK` under CLAUDE.md's
`r3-perframe-0.90` bands — 0.0% of the 89 frames hit the per-frame ≥ 0.90 STRUCK trip. The
real-data overlap (0.8494) sits well above the synthetic proxy's 0.7346 ceiling above, which
undersold it: a fixed-`d` fractional difference of log price tracks a 200-bar distance-to-SMA
closely on these frames. Disclosed, not struck — the column ships as-is; `ffd` stays
registered, no module/wiring/test removal needed. Gate C's real-data counts remain owed (no
parent-repo access in this worktree).
