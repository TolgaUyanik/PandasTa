# entlz — measured

> **Status: Gates A-F pass. SHIP.** `ENTLZ_20` cleared Gate E (max |ρ| 0.5985 vs `stdev`, well
> under the 0.76 ship line). `entlz` stays in `Category`.

`ENTLZ_20` is the plug-in Shannon entropy of a sign-encoded return sequence over a rolling
20-bar window, per issue #11 (AFML ch. 18 "Entropy Features": the sources are plug-in,
Lempel-Ziv, and Kontoyiannis estimators). Module `pandas_ta/statistics/entlz.py`, tests
`tests/test_entlz.py`, branch `issue-11-entlz`.

## Decisions the issue left open

The issue lists three decisions and leaves them to the port. No human was available to ask
(headless session), so each took the most conservative, smallest-scope reading:

1. **Encoding: sign, not k quantile bins.** Quantile bins need a boundary fit on past data
   only (a second causality surface) for no benefit this port's scope needs. Sign has no fit
   step, and it is the encoding the issue's own "scale-free by construction" line describes.
   ASSUMPTION, not measured against quantile bins.
2. **Estimator: plug-in, not Lempel-Ziv or Kontoyiannis.** The issue states plug-in is
   simplest and LZ needs a longer window; it does not require LZ. LZ is not built here.
   ASSUMPTION.
3. **Window: `length=20`.** An unexamined default matching this fork's other short-lookback
   momentum defaults (10-14) rounded up for a 3-symbol frequency estimate to have a chance of
   stabilizing. Not tuned or measured against another length. ASSUMPTION.
4. **Alphabet: 3 symbols (up / down / flat), not 2.** `np.sign(close.diff())` naturally
   produces `{-1, 0, +1}`; collapsing flat into one of the other two would need an arbitrary
   tie-breaking rule with its own edge cases (see `pfe`'s round-trip bug, `docs/PfeMeasured.md`).
   Keeping all three avoids inventing that rule. ASSUMPTION.

## What it is, and what it is not

`p_s` = fraction of the trailing `length` returns with sign `s`, for `s` in `{-1, 0, +1}`.
`ENTLZ = -sum_s p_s * log(p_s, base)` (default base 2, so bits), range `[0, log2(3)]` =
`[0, 1.5850]`. Zero means every return in the window shares one sign (perfectly predictable
direction); the maximum means all three signs are equally frequent.

**Not `pandas_ta.statistics.entropy` (`ENTP`).** That column is the Shannon entropy of the
price LEVEL's share of a rolling window (`p = close / close.rolling(n).sum()`) — not a
function of returns, and not sign-based at all. The issue's own overlap note names this
distinction; it is confirmed again here by the pre-screen below (ρ −0.23, not near redundant).

**Is it already shipped?** A grep of the repo (excluding the untracked `docs/pine/`) for
`entropy`, `lempel`, `kontoyiannis`, `sign.*entrop` finds only `pandas_ta/statistics/entropy.py`
(the different object above). No return-sign entropy is shipped.

## Gates

Environment: this worktree's Python/pandas/numpy (see `docs/IndicatorDictionary.md` header:
pandas 2.3.3). `tests/test_entlz.py`: 22 of 22 passing.

| Gate | Result |
|---|---|
| A | **Against an independent reference**: a nested-loop frequency count of `{-1,0,+1}` per window, written from the formula, not the module, on a 400-bar tick-rounded walk (seed 11). Max\|diff\| **0.0** at length 20, 9 and 2 (n 1,180 / 1,191 / 1,198) — the plug-in formula has no rounding-sensitive step, so this is exact, not merely close. **Hand-computed closed forms**: a pure trend (all-same-sign returns) reads exactly 0; a perfect +1/-1 alternation reads exactly 1 bit; a 9-bar window split 3/3/3 across the three signs reads exactly `log2(3)` = 1.584963. A flat-price window (every return exactly 0) reads exactly 0, not NaN. |
| B | Future-perturbation by a deterministic single-bar sign flip (not a random future tail — a 3-symbol alphabet can tie on a random future by chance). The real module leaks at **0 of 32** offsets. Two one-bar look-ahead mutants (`importlib` source read, `exec`'d in memory) — the return series shifted one bar ahead, and the rolling frequency window shifted one bar ahead — are each shown to change the output, then caught at **32 of 32**. `test_the_random_future_convention_ties_on_this_alphabet` keeps the whole-tail-replacement convention `pfe`/`cusum` use as a pinned, reproducible counter-example: both mutants are caught at only **29 of 32** offsets that way, 3 short of the deterministic flip's 32/32 — measured by that test, re-run it to reproduce. |
| C | **Synthetic.** Gate E's run confirms real-data reachability indirectly: 397,069 non-NaN `ENTLZ_20` values pooled over the 89 ALTPORT-1 frames (`overlap_max.csv`), so the column fires on real data at scale; it is not re-derived as a standalone fires/n count here. 1,200-bar tick-rounded walk (seed 11, σ 1.5%, tick 0.01): 1,180 non-NaN (20-bar warm-up), **13 distinct values** (expected: frequencies are quantized to `k/20`, so the plug-in estimator at a fixed window length has a bounded, small set of reachable values), 0 reading exactly 0 on this particular walk, range [0.4690, 1.2345] against the `log2(3)` = 1.5850 bound. A composite 50-bar-trend + 200-bar-chop frame (length 20) demonstrates both ends: 230 non-NaN, 11 distinct, **31 bars reading exactly 0** (the trend) and **127 bars reading ≥ 0.99** bit (the chop, near the 2-symbol bound). |
| D | **Stronger than the usual x8/x64 bit-identical check.** `sign(k * x) == sign(x)` for any `k > 0`, exactly (zero returns stay exactly zero under any scalar, since `k*a - k*a` is exact in IEEE754; nonzero returns cannot flip sign from ULP-level rounding). Measured, not assumed: close ×8, ×64, ×10 AND ×3.7 are **all bit-identical**, with matching NaN masks — the ×10/×3.7 pair needs no tolerance band at all, unlike every price-level or log-return statistic in this fork. `0 < fires < n` is replaced by "not constant" for this continuous column: see Gate C's distinct-value counts. |
| E | **Measured 2026-10-31**, run `is11-entlz-70e0caec`, 89 ALTPORT-1 frames, 687 comparators (329 compute_all + 358 manifest), pooled n 397,069 (one `squeeze_SQZ_NO` comparator dropped as degenerate/constant). `ENTLZ_20`: max \|ρ\| **0.5985** against `stdev` (compute_all, n 397,069); per-frame max median \|ρ\| **0.5780** (also vs `stdev`, 89 frames, 0.0% of frames ≥ 0.90); manifest-only max \|ρ\| 0.4508 against `Pct_Up_Days_63` (n 396,179). Both pooled and per-frame figures sit under the 0.76 SHIP line (`r3-perframe-0.90` schema). **Verdict: SHIP.** Nearest neighbors besides `stdev` are other dispersion/range columns (`mad` −0.5967, `variance` −0.5965, `LINREG_DEV` −0.5809, `ATR` −0.5743) — expected, since entropy of a 3-symbol sign alphabet and a dispersion statistic both track how "mixed" a window is, but none crosses redundancy. Recorded in `docs/gate_e_ledger.csv`. |
| F | **This repo only**, full `python -m pytest -q`: **2 failed, 3,531 passed, 83 skipped.** Both failures are CI's two `--deselect`s (`test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`, the pre-existing known break; `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`, needs `../AlternativeRepos`) — neither touches `entlz`. `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` now passes with the recorded row. Parent repo (`Backtesting`) not run from this worktree; the launcher runs both suites in clean worktrees separately. |

## Pre-screen (NOT Gate E)

Spearman ρ of `ENTLZ_20` against in-package candidates, same 1,200-bar synthetic walk used
above (informal; Gate E uses the production engine's 687-comparator set over 89 real BIST
frames, not this):

| comparator | ρ |
|---|---|
| `ENTP_10` (price-level entropy) | −0.2326 |
| `STDEV_20` | −0.2681 |
| `CUSUM_100` | −0.2659 |
| `RSX_14` | −0.2355 |
| `ENTP_10` ≈ `CMO_14` ≈ `RSI_14` | ≈ −0.23 |
| `ER_10` | −0.1483 |
| `SKEW_20` | −0.0728 |
| `KPSS_100` | 0.0451 |

All magnitudes are well under the disclosure band (0.76); none suggests redundancy. This is a
proxy on one synthetic walk, not a prediction of the Gate E result.

## Reproduce

    python docs/measure_entlz_proxy.py

## Closed

Gate E measured 2026-10-31, SHIP (max |ρ| 0.5985 < 0.76). `entlz` ships as-is; no revert
needed. Issue #11 closes with this file as the Gate E receipt.
