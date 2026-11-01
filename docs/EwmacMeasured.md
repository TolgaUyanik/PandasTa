# EWMAC — Carver's volatility-normalised EMA crossover — measured (`ewmac`)

`(EMA_fast(close) - EMA_slow(close)) / sigma`, where `sigma` is the recent standard
deviation of daily price changes in price points. Carver gives six speed pairs: 2:8,
4:16, 8:32, 16:64, 32:128, 64:256, with `alpha = 2 / (L + 1)`. Found by the ResearchIntel
RAG scan of 2026-10-24, round 3 (`PandasTaIndicatorCandidates-2026-10-22.md`, section
*Round 3*), issue #29.

**Status: measured revert. Gate E STRUCK five of the six pairs; only 64:256 survives,
at DISCLOSE_GAP.** `ewmac` stays in `Category` (`EWMAC_64_256_35` only), so a
`df.ta.strategy()` sweep in the parent repo picks up one column, not six.

Shipped: `pandas_ta/momentum/ewmac.py`, one column `EWMAC_64_256_<vol_length>` (default
`EWMAC_64_256_35`). Tests: `tests/test_ewmac.py` (12). Numbers:
`python docs/measure_ewmac.py`. Environment: pandas 2.3.3, numpy 1.26.4, Python 3.11.2.
Measured 2026-11-01 (first run, six columns); Gate E re-run 2026-11-01 (this session,
record only — the launcher ran the harness, this session applied the bands).

## Gate A decisions (both open questions in the issue)

The issue leaves two things open at Gate A. No book or web access in this session, so
both are decided on the most conservative reading available (smaller scope, matching what
Carver's own open-sourced `pysystemtrade` does) and flagged as ASSUMPTIONS, not citations:

1. **Which `sigma`.** Carver's own form, not a simple rolling window: an EWMA standard
   deviation of `close.diff()` (`pandas`' `.ewm(adjust=False).std()`), not a plain
   `.rolling().std()`. The EWMA span for `sigma` (`vol_length`, default 35) is the value
   `pysystemtrade` uses for `robust_vol_calc`, recalled, not cited to a page number — an
   explicit guess, flagged the same way `docs/PfeMeasured.md` flags its own unsourced
   choices. (The original port's further choice — one shared `sigma` across all six
   columns rather than six independently-derived ones — is now moot: only one column
   ships, so there is nothing left to share it with. `test_sigma_is_shared_not_per_pair`
   was removed from `tests/test_ewmac.py` with the five reverted columns, since the
   property it pinned no longer applies.)
2. **Scalar and cap.** Not shipped. The issue's own Gate A note says a tree does not need
   the scalar; Carver's published forecast scalars (10.6 down to 1.87) and the |forecast|
   <= 20 cap are a position-sizing device for his trading system, not a feature transform.
   `ewmac` ships the raw ratio only.

No forecast-scalar / cap parameter exists at all — adding one that is never read would be
an unused knob, so it was left out rather than wired in and ignored.

## Kaufman's Divergence Index: same family, not built separately

Kaufman (2013) ch09 describes a "volatility-adjusted difference between two moving
averages" (`(MA10 - MA40) / stdev(deltaP, 40)`), flagged by the issue as possibly having a
garbled, squared stdev in the PDF extraction. Not checked against the physical book (no
library access in this session) — `ewmac`'s own `sigma` is unsquared (`.std()`, not
`.var()`), which is scale-free by construction (Gate D below) and therefore cannot be the
squared form Kaufman's garbled extraction might show. Carver's EWMAC and Kaufman's
Divergence Index are the same mathematical family (an MA-difference over a volatility of
price changes); shipping `ewmac` covers both without a second module. If the PDF garbling
turns out to describe a materially different indicator, that is a separate port, not a
flaw in this one.

## Gate E — measured, bands applied

The issue's own pre-registered expectation ("high redundancy risk against `MACD_pct`,
`MACD_Hist_ATR` and `PPO`, with the slow pairs (32:128, 64:256) having the best chance of
adding information") was directionally right about *which* pair would survive, but wrong
about the comparators: nothing struck against the engine's `MACD_pct` itself. Harness:
`gate_e_overlap.py run --module pandas_ta.momentum.ewmac`, `compute_all` (329 cols) ∪
`ml_features` manifest `1d` (358 cols) = 687 comparators, 89 frozen ALTPORT-1 BIST frames,
bands `r3-perframe-0.90`. Run `is29-ewmac-177f3161`, recorded 2026-11-01.

| column | pooled max \|rho\| | against | n | per-frame max median \|rho\| | verdict |
|---|---|---|---|---|---|
| `EWMAC_2_8_35` | 0.9739 | `pgo` | 397,603 | 0.9751 | **STRUCK** |
| `EWMAC_4_16_35` | 0.9829 | `smi_SMI_5_20_5` | 397,158 | 0.9830 | **STRUCK** |
| `EWMAC_8_32_35` | 0.9945 | `tsi` | 396,713 | 0.9946 | **STRUCK** |
| `EWMAC_16_64_35` | 0.9175 | `ICHI_CHIKOU_VS_CLOUD` | 391,996 | 0.9148 | **STRUCK** |
| `EWMAC_32_128_35` | 0.9298 | `Dist_to_SMA_200_pct` | 381,138 | 0.9276 | **STRUCK** |
| `EWMAC_64_256_35` | 0.8744 | `SMA_200_Slope_pct` | 380,693 | 0.8682 | DISCLOSE_GAP |

Bands (CLAUDE.md Gate E row, `r3-perframe-0.90`): STRUCK if pooled \|rho\| >= 0.90 or the
per-frame max median >= 0.90; DISCLOSE_GAP 0.80 <= rho < 0.90. All five fast/medium pairs
cross the STRUCK line on both the pooled and per-frame statistic (100% of the 89 frames at
>= 0.90 for the three fastest; 83-87% for 16:64 and 32:128). Only `EWMAC_64_256_35` lands
under 0.90, at DISCLOSE_GAP — consistent with the issue's own guess that the slow pairs had
the best chance, because the engine has no MACD-family column that slow; its actual nearest
comparator turned out to be `SMA_200_Slope_pct`, not `MACD_Hist_ATR` or `PPO` as guessed.

**Decision: revert the five STRUCK columns, ship `EWMAC_64_256_35` only.** No waiver exists
or was requested for any of the five (`ALLOWED_WAIVERS` in `tests/test_gate_e_ledger.py`
only covers `pfe` and `kalman_trend`'s pre-ledger columns) — a STRUCK column without a
waiver is reverted per CLAUDE.md's Gate E row and `tests/test_gate_e_ledger.py`'s own rule
(`test_struck_rows_carry_the_waiver_for_this_exact_measurement`). `docs/gate_e_ledger.csv`'s
five STRUCK ewmac rows were removed by `docs/measure_ewmac_ledger_fix.py` (the same pattern
as `docs/measure_crsi_ledger_fix.py` for issue #21); the surviving `EWMAC_64_256_35` row is
left recorded but now describes code that changed underneath it (editing `ewmac.py` to drop
five columns changes the module's sha1), so it goes **owed** again — `tests/test_gate_e_ledger.py::test_row_still_describes_its_module[ewmac:EWMAC_64_256_35]`
fails locally in this session's own `python -m pytest -q` run below, exactly as CRSI's and
correlation_cycle's revert commits did between their revert and their post-revert Gate E
re-run. A future session re-running Gate E on this post-revert tree records a fresh row.

## Gate C — real-data reachability (from the Gate E run)

Not synthetic-only anymore: the Gate E run's own `non_nan` / `non_zero` / `pooled_bars`
fields give real counts on the 89 BIST frames, pooled. For the surviving column,
`EWMAC_64_256_35`: 398,669 of 398,849 pooled bars non-NaN (99.95%), all 398,669 non-zero —
the only non-firing bars are `sigma`'s own 2-bar EWMA-std warm-up, matching the synthetic
probe's finding that the warm-up is `sigma`'s, not the (much longer) 256-bar EMA's, since
`ema(..., sma=False)` under `adjust=False` emits from bar 0.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass (formula reassembled independently of the module's own code path, plus a hand-computed 3-bar EMA recursion, both re-targeted to the surviving 64:256 pair after the revert) | hand-computed 64:256 EMA recursion on `close=[10,11,13,...]` matches the module's numerator (`out * sigma`) to 1e-9; a 400-bar walk's full formula, rebuilt in the test directly from `close.ewm(span=L, adjust=False).mean()` and `close.diff().ewm(span=35, adjust=False).std()`, matches to 1e-9 |
| B Causality | pass | 31-offset future-rewrite sweep (rewrite bars `>= j` with an unrelated walk, demand bars `< j` unchanged): real module 0 leaks at all 31 offsets. Two look-ahead mutants (`sigma`: shift the diff input by -1; `fastma`: shift the fast EMA by -1) are each proved live, then caught at 31 of 31 |
| C Reachability | real data (from the Gate E run) | `EWMAC_64_256_35`: 398,669 / 398,849 pooled bars non-NaN (99.95%) across the 89 BIST frames, all non-zero; the 2-bar-per-frame gap is `sigma`'s own EWMA-std warm-up |
| D Scale-free | pass | x8 / x64 bit-identical (EMA and EWMA-std are both linear/homogeneous in `close` under exact power-of-two floating-point scaling); x10 / x3.7 max abs diff measured at 1.4e-13 / 1.6e-13 (well under the 1e-9 the test asserts), NaN masks matching; `0 < 1,198 fires < 1,200` on the synthetic probe, so a constant column cannot pass |
| E Attribution | **measured, five STRUCK and reverted, one DISCLOSE_GAP shipped** | see the Gate E table above; `is29-ewmac-177f3161`, recorded in `docs/gate_e_ledger.csv` |
| F Suites | this repo only; parent repo not run by this session | `python -m pytest -q`: 3 failed / 3,920 passed / 83 skipped. Two pre-exist this port, named in `CLAUDE.md`'s *Known breaks*: `test_pine_coverage_csv::test_audited_rows_carry_their_evidence` (`docs/pine/` untracked) and `test_altrepo_talib_csv::test_regenerating_reproduces_the_committed_rows` (needs the sibling `../AlternativeRepos` checkout, not on this machine). The third, `test_gate_e_ledger.py::test_row_still_describes_its_module[ewmac:EWMAC_64_256_35]`, is the **expected** owed-row failure from this session's revert edit (see Gate E section) — the same state CRSI's and correlation_cycle's revert commits left between their revert and their post-revert Gate E re-run |

## Proxy overlap (superseded by real Gate E, kept for the record)

Spearman rho of each `EWMAC_*` column (all six, before the revert) against
`MACD_12_26_9 / close * 100` and `NATR_14`, on one synthetic tick-rounded GBM walk
(sigma=0.02, seed 11, tick 0.05, n=1,200). This guessed at `MACD_pct`/`NATR_14` as the
nearest comparators and got the *direction* right (fast pairs riskier, slow pairs safer)
but not the actual nearest comparators Gate E found (`pgo`, `smi`, `tsi`,
`ICHI_CHIKOU_VS_CLOUD`, `Dist_to_SMA_200_pct`, `SMA_200_Slope_pct` — none of them `MACD_pct`,
`MACD_Hist_ATR` or `PPO` as the issue guessed):

| column | rho vs `MACD_pct(12,26)` | rho vs `NATR_14` | n | Gate E verdict |
|---|---|---|---|---|
| `EWMAC_2_8_35` | 0.4503 | -0.1621 | 1,175 | STRUCK (reverted) |
| `EWMAC_4_16_35` | 0.7963 | -0.2041 | 1,175 | STRUCK (reverted) |
| `EWMAC_8_32_35` | 0.9927 | -0.2478 | 1,175 | STRUCK (reverted) |
| `EWMAC_16_64_35` | 0.8616 | -0.2761 | 1,175 | STRUCK (reverted) |
| `EWMAC_32_128_35` | 0.4945 | -0.2372 | 1,175 | STRUCK (reverted) |
| `EWMAC_64_256_35` | 0.1360 | -0.1560 | 1,175 | DISCLOSE_GAP (shipped) |

The proxy's own rho against the two guessed comparators was a poor predictor of the real
Gate E verdict (e.g. `EWMAC_16_64_35` scored lower against `MACD_pct` than `EWMAC_4_16_35`
yet still struck, against a comparator the proxy never tested) — a reminder that a
synthetic one-walk, two-comparator proxy is not a substitute for the real 89-frame,
687-comparator run.

## Closed

1. Gate E run `is29-ewmac-177f3161` recorded in `docs/gate_e_ledger.csv`.
2. Bands applied: `EWMAC_2_8_35`, `EWMAC_4_16_35`, `EWMAC_8_32_35`, `EWMAC_16_64_35`,
   `EWMAC_32_128_35` STRUCK, reverted (no waiver). `EWMAC_64_256_35` DISCLOSE_GAP, shipped.
3. Gate C filled from the same real frames (real reachability counts above).
4. `docs/IndicatorDictionary.md` and `docs/MLCompanionContract.md` regenerated /
   updated for the one surviving column (601 tagged columns, 246 `SF`, down from 606 / 251).
5. `docs/gate_e_ledger.csv`'s five STRUCK ewmac rows removed (`docs/measure_ewmac_ledger_fix.py`);
   the surviving `EWMAC_64_256_35` row is now owed again (module sha1 changed by the revert
   edit) — a future Gate E re-run on this tree records a fresh row, as CRSI's and
   correlation_cycle's revert commits did.
6. Both suites: this repo's `python -m pytest -q` run: 3 failed / 3,920 passed / 83 skipped
   (two pre-existing known breaks, one expected owed Gate E row — see Gate F above). Parent
   repo not run by this session.
