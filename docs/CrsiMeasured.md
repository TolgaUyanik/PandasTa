# Connors RSI — measured (`crsi`)

Connors Research's composite momentum oscillator (Kaufman 2013, ch. 9 "Momentum and
Oscillators"): `(RSI(close, 3) + RSI(streak, 2) + PercentRank(1-bar return, 100)) / 3`, where
`streak` is the signed count of consecutive up or down closes. Found by the ResearchIntel RAG
scan of 2026-10-22, round 2 (report `PandasTaIndicatorCandidates-2026-10-22.md`, 5 hits).
Kaufman 2013 was not available on this machine, so nothing below is checked against it line
by line; the formula is the one quoted in the issue, independently re-derived in
`tests/test_crsi.py::test_matches_an_independent_loop`.

**Status: SHIPPED, partially -- a measured revert on 2 of 3 columns.** Gate E (below) struck
the composite (`CRSI_3_2_100`) and the percent-rank term (`CRSI_PCTRANK_100`); both are
removed. Only the streak term (`CRSI_STREAK_2`) ships, at DISCLOSE_GAP. The issue's "decide
whether to ship the composite, the components, or only the streak term, and let Gate E settle
it" is settled: only the streak term.

Shipped: `pandas_ta/momentum/crsi.py`, one column -- `CRSI_STREAK_2`, bounded `[0, 100]`.
Tests: `tests/test_crsi.py` (12). Environment: pandas 2.3.3, numpy 1.26.4, Python 3.11.2.
Built 2026-10-31, Gate E measured and composite/pctrank reverted 2026-11-01.

## What is NOT shipped, and why

`RSI(close, 3)` was never shipped as its own column: at the default `rsi_length=3` it is
exactly `ta.rsi(close, 3)`, already available from the shipped `rsi` indicator -- shipping it
again would be a redundant column (CLAUDE.md's non-redundant rule). This confirmed the
issue's guess ("the RSI(3) term probably restates `rsi`") without needing Gate E: it is a
literal restatement, not a correlation.

`CRSI_3_2_100` (the composite) and `CRSI_PCTRANK_100` (the percent-rank term) were built,
Gate E-measured, and **reverted**: both struck (pooled |rho| >= 0.90 on 100% of 89 frames --
see the Gate E table below). The module, `Category`/accessor wiring and test suite now cover
only the streak term; `CRSI_3_2_100` and `CRSI_PCTRANK_100` no longer exist anywhere in the
package. `docs/measure_crsi_proxy.py`'s proxy table (next section) was run before Gate E and
is kept as-is, as the historical record of what the pre-revert build looked like against this
package's own oscillators -- it still named all three columns at the time it ran.

## Design decisions

| decision | why |
|---|---|
| `streak[0] = 0`, and 0 on any unchanged close | there is no prior close to compare the first bar against; an exact tie breaks a run rather than extending it either direction |
| `RSI(streak, streak_length)` reuses the shipped `rsi()` formula verbatim on the streak series, not a different smoothing | Connors' definition feeds the streak through an ordinary Wilder RSI; a bespoke smoothing would not be "RSI of the streak" |

## Causality

Future-perturbation over 28 offsets (150 to 1085, step 35, past the warm-up), on the shipped
streak term: **real module 0 leaks**. One look-ahead mutant (`importlib` source read, one
line replaced, `exec`'d in memory), proved live then **caught at 28 of 28**:

* `streak_future` -- the streak's direction read 10 bars ahead (`close.shift(-10) - close`
  instead of `close.diff()`).

(A second mutant, `pctrank_centered` -- the percent-rank window centered instead of trailing,
the `dpo`-style `centered=True` bug class CLAUDE.md flags -- was tested against the pre-revert
build and also caught 28/28; it no longer applies now that `_percent_rank` is removed.)

The perturbation itself had to be redesigned mid-port: splicing in an unrelated random
walk's tail (the `pfe`/`kalman_trend` precedent) makes a future *sign* read's detection
rate depend on the two walks' relative level at that specific bar index, which drifts over
a long GBM path and is NOT close to the expected 50/50 per offset -- observed well short of
28/28 across several attempts during development (informal, not reproducible from a
committed script, unlike every other number in this file). Shifting the SAME series
by a huge constant (+/-1e6) instead, and counting a leak if EITHER direction shows a
difference, closed the gap to 28/28: a forced-positive read can coincide with a bar that
was already locally trending up (and so go undetected on its own), but the forced-negative
read then cannot also coincide.

## Gates

| gate | result | evidence |
|---|---|---|
| A Correctness | self-consistency (no page-citable source on this machine) | matches an independent loop (Wilder RSI via plain `ewm`, streak via a plain Python loop, neither calling `pandas_ta.momentum.rsi` or the module's own helper) to 1e-9 on a 400-bar walk; hand-computed example: streak `[0, 1, 2, -1, -2, -3, 1]` for closes `10,11,12,11,10,9,10` |
| B Causality | pass | 0 real leaks / 28 offsets; mutant caught 28/28 (see above) |
| C Reachability | synthetic + real (via Gate E's 89-frame pooled run) | synthetic: 1,200-bar tick-rounded walk (seed 11, tick 0.05), `CRSI_STREAK_2` 1,198 finite / 1,198 nonzero. Real: Gate E's `non_nan`/`non_zero` columns on 398,669 pooled bars across 89 BIST frames -- 398,669 non-NaN, 398,636 non-zero (`0 < fires < n` holds) |
| D Scale-free | pass | x8 / x64 bit-identical (max diff 0.0, matching NaN masks); x10 / x3.7 within 1e-9; `0 < fires < n` with > 100 distinct values |
| E Attribution | **measured 2026-11-01, see table below** | `gate_e_overlap.py run --module pandas_ta.momentum.crsi` against `compute_all` union the `ml_features` manifest `1d`, 89 ALTPORT-1 BIST frames, bands `r3-perframe-0.90`. Recorded in `docs/gate_e_ledger.csv` |
| F Suites | this repo green after the revert | `python -m pytest -q`: 3,827 passed / 83 skipped / 2 failed (2026-11-01). Both failures are pre-existing and unrelated to this port: `test_pine_coverage_csv::test_audited_rows_carry_their_evidence` (CLAUDE.md's known break) and `test_altrepo_talib_csv::test_regenerating_reproduces_the_committed_rows` (needs the sibling `../AlternativeRepos` checkout, not present). Parent repo run by the launcher, not in this session |

## Gate E (measured 2026-11-01)

**First run**, `is21-crsi-d7238138`, `pandas_ta_src_sha1` `51291e75b0a8f24bb6d5bcb35db2b3a46a4baf1f`
(the pre-revert tree, three columns), 89 ALTPORT-1 BIST daily frames, 687 comparators
(`compute_all` 329 + `ml_features` manifest `1d` 358), canary `AKBNK.IS, BIENY.IS, AGHOL.IS,
SASA.IS bit-equal`.

| column | max \|rho\| | against | n | perframe max median \|rho\| | verdict |
|---|---|---|---|---|---|
| `CRSI_3_2_100` (composite) | 0.9265 | `log_return` | 389,860 | 0.9257 (100% of 89 frames >= 0.90) | **STRUCK** -- reverted |
| `CRSI_STREAK_2` | 0.8362 | `increasing` | 398,669 | 0.8421 (0% of 89 frames >= 0.90) | **DISCLOSE_GAP** -- shipped |
| `CRSI_PCTRANK_100` | 0.9717 | `log_return` | 389,860 | 0.9769 (100% of 89 frames >= 0.90) | **STRUCK** -- reverted |

**Confirmation run**, `is21-crsi-81723757`, `pandas_ta_src_sha1` `8455c2a68f1588ec60e8de4173a93265edbe0d57`
(the post-revert tree, one column), same 89 frames and 687 comparators, same canary, launched
by the issue-solver against the committed `pandas_ta/momentum/crsi.py` as it ships today:

| column | max \|rho\| | against | n | perframe max median \|rho\| | verdict |
|---|---|---|---|---|---|
| `CRSI_STREAK_2` | 0.8362321121401246 | `increasing` | 398,669 | 0.8420626737909467 (0% of 89 frames >= 0.90) | **DISCLOSE_GAP** -- shipped |

Identical to the first run's `CRSI_STREAK_2` row to full precision -- the revert touched only
the composite/pctrank code, not the streak computation, as the design decisions section above
already noted. Recorded in `docs/gate_e_ledger.csv` (`measured` 2026-11-01, run
`is21-crsi-81723757`, superseding the first run's row for the same column).

Applying CLAUDE.md's `r3-perframe-0.90` bands: `CRSI_3_2_100` and `CRSI_PCTRANK_100` are both
at or above the 0.90 pooled threshold, with their respective top comparator (`log_return`) at
or above 0.90 median on 100% of the 89 frames -- struck, no waiver sought, removed. The
composite's result is not surprising: `CRSI_3_2_100` is the straight average of a column
(`CRSI_PCTRANK_100`) that itself struck against the same comparator, `log_return`, so the
composite inherits most of that correlation. `CRSI_STREAK_2` is below the 0.90 line on every
measure (pooled 0.8362, per-frame median 0.8421, 0% of frames over 0.90) -- DISCLOSE_GAP, not
STRUCK, so it ships, matching the issue's own hypothesis ("the streak RSI... are the new
parts") and the proxy table below (streak was the least-correlated of the three against this
package's own oscillators).

## Proxy overlap (NOT Gate E, pre-revert, kept for context)

Spearman rho against this package's own `[0, 100]`-bounded oscillators, one synthetic GBM
walk (sigma = 0.02, seed 1), n = 2,899, computed before Gate E ran -- against all three
pre-revert columns:

| comparator | `CRSI_3_2_100` | `CRSI_STREAK_2` | `CRSI_PCTRANK_100` |
|---|---|---|---|
| `ROC_1` | **0.9214** | 0.7461 | **0.9898** |
| `RSI_3` | 0.8485 | 0.5846 | 0.6534 |
| `WILLR_14` | 0.6497 | 0.3684 | 0.4634 |
| `ROC_5` | 0.5968 | 0.2989 | 0.4023 |
| `RSI_14` / `CMO_14` | 0.4646 | 0.2217 | 0.2852 |
| `STOCHRSIk_14_14_3_3` | 0.3880 | 0.1326 | 0.1917 |

This proxy only covered this package's own momentum oscillators, not the engine's
687-comparator set, and flagged `CRSI_PCTRANK_100` as close to a rank-transform of `ROC_1`
(rho 0.9898) and `CRSI_STREAK_2` as the most novel of the three (max 0.7461). Gate E (above)
confirmed both directions: `CRSI_PCTRANK_100` struck (against the engine's `log_return`, not
`ROC_1`, but the same underlying signal -- a return series), and `CRSI_STREAK_2` cleared.

## To close

Closed. Nothing further owed:

1. ~~Run `gate_e_overlap.py`~~ -- done by the launcher, recorded above.
2. ~~Record the run~~ -- `python docs/gate_e_ledger.py record <run dir> --measured 2026-11-01`,
   in `docs/gate_e_ledger.csv`.
3. ~~Fill Gate C from real frames~~ -- see the Gate C row above, from Gate E's own non-NaN/
   non-zero counts.
4. ~~Apply the bands, revert struck columns~~ -- `CRSI_3_2_100` and `CRSI_PCTRANK_100`
   removed from `pandas_ta/momentum/crsi.py`, `tests/test_crsi.py` rewritten to cover only
   the streak term, `docs/IndicatorDictionary.md` regenerated, `docs/MLCompanionContract.md`'s
   SF count corrected (243 -> 241), `tests/test_altport2_ports.py`'s narrative comment
   updated. `crsi` itself stays in `Category` (one indicator name, now one column) -- not a
   full module revert, since one column survived. The two STRUCK rows were dropped from
   `docs/gate_e_ledger.csv`; the surviving `CRSI_STREAK_2` row's `module_sha1` was updated to
   the edited file (its `output_fp` is unchanged -- the streak computation itself was not
   touched, only the composite/pctrank code around it was deleted, confirmed by
   `docs/measure_crsi_ledger_fix.py`, which recomputes both from the current tree the same
   way `gate_e_ledger.py record` would, since `record` itself refuses to re-run against an
   edited file).
5. ~~Run both repos' suites~~ -- this repo's run below; the parent repo's suite runs in the
   launcher's clean worktree, not in this session.
