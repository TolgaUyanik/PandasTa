# EWMAC — Carver's volatility-normalised EMA crossover — measured (`ewmac`)

`(EMA_fast(close) - EMA_slow(close)) / sigma`, where `sigma` is the recent standard
deviation of daily price changes in price points. One column per Carver speed pair: 2:8,
4:16, 8:32, 16:64, 32:128, 64:256, with `alpha = 2 / (L + 1)`. Found by the ResearchIntel
RAG scan of 2026-10-24, round 3 (`PandasTaIndicatorCandidates-2026-10-22.md`, section
*Round 3*), issue #29.

**Status: Gates A, B, D cleared; Gate C synthetic only (real-data counts owed); Gate E:
pending, run by issue-solver after this session.** `ewmac` is in `Category`, so any
`df.ta.strategy()` sweep in the parent repo picks it up.

Shipped: `pandas_ta/momentum/ewmac.py`, six columns `EWMAC_<fast>_<slow>_<vol_length>`
(defaults `EWMAC_2_8_35` ... `EWMAC_64_256_35`). Tests: `tests/test_ewmac.py` (13).
Numbers: `python docs/measure_ewmac.py`. Environment: pandas 2.3.3, numpy 1.26.4, Python
3.11.2. Measured 2026-11-01.

## Gate A decisions (both open questions in the issue)

The issue leaves two things open at Gate A. No book or web access in this session, so
both are decided on the most conservative reading available (smaller scope, matching what
Carver's own open-sourced `pysystemtrade` does) and flagged as ASSUMPTIONS, not citations:

1. **Which `sigma`.** Carver's own form, not a simple rolling window: an EWMA standard
   deviation of `close.diff()` (`pandas`' `.ewm(adjust=False).std()`), not a plain
   `.rolling().std()`. Further choice inside that, not stated by the issue: **one shared
   `sigma` across all six columns**, not six independently-derived ones at each pair's own
   span. This matches Carver's `robust_vol_calc` (one recent-volatility estimate reused by
   every trading-rule variation of a given instrument) and is pinned by
   `test_sigma_is_shared_not_per_pair` in `tests/test_ewmac.py`. The EWMA span for `sigma`
   (`vol_length`, default 35) is the value `pysystemtrade` uses for `robust_vol_calc`,
   recalled, not cited to a page number — an explicit guess, flagged the same way
   `docs/PfeMeasured.md` flags its own unsourced choices.
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

## Overlap, pre-registered

The issue pre-registers "high redundancy risk" against `MACD_pct`, `MACD_Hist_ATR` and
`PPO`, with the slow pairs (32:128, 64:256) flagged as having the best chance of adding
information, because the engine has no MACD-family column that slow. The proxy below
(synthetic, not Gate E) is directionally consistent with that guess.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass (formula reassembled independently of the module's own code path, plus a hand-computed 3-bar EMA recursion) | hand-computed 2:8 EMA recursion on `close=[10,11,13,...]` matches the module's numerator (`out * sigma`) to 1e-9; a 400-bar walk's full formula, rebuilt in the test directly from `close.ewm(span=L, adjust=False).mean()` and `close.diff().ewm(span=35, adjust=False).std()`, matches all six columns to 1e-9; a dedicated test pins that all six columns divide by the SAME `sigma` series |
| B Causality | pass | 31-offset future-rewrite sweep (rewrite bars `>= j` with an unrelated walk, demand bars `< j` unchanged): real module 0 leaks at all 31 offsets. Two look-ahead mutants (`sigma`: shift the diff input by -1; `fastma`: shift the fast EMA by -1) are each proved live, then caught at 31 of 31 |
| C Reachability | synthetic only | 1,200-bar tick-rounded walk (seed 11, tick 0.05): every one of the six columns has 1,198 of 1,200 bars non-NaN, all 1,198 nonzero, 1,198 distinct values. The 2 non-firing bars are `sigma`'s own 2-bar warm-up (`close.diff()`'s leading NaN plus `.ewm().std()`'s own minimum-points requirement), not the 256-bar EMA warm-up — EMA's own `adjust=False` recursion starts emitting from bar 0. **Real-data counts owed** |
| D Scale-free | pass | x8 / x64 bit-identical on all six columns (EMA and EWMA-std are both linear/homogeneous in `close` under exact power-of-two floating-point scaling); x10 / x3.7 max abs diff measured between 1.0e-13 and 1.1e-12 across the six columns (well under the 1e-9 the test asserts), NaN masks matching; `0 < 1,198 fires < 1,200` per column, so a constant column cannot pass |
| E Attribution | **PENDING** | `gate_e_overlap.py run --module pandas_ta.momentum.ewmac`, run by issue-solver after this session |
| F Suites | this repo only; parent repo not run by this session | `python -m pytest -q`: 3 failed / 3,914 passed / 83 skipped. None of the 3 failures name `ewmac`. Two pre-exist this port and are named in `CLAUDE.md`'s *Known breaks*: `test_pine_coverage_csv::test_audited_rows_carry_their_evidence` (`docs/pine/` untracked) and `test_altrepo_talib_csv::test_regenerating_reproduces_the_committed_rows` (needs the sibling `../AlternativeRepos` checkout, not on this machine). The third, `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, is the **expected** failure until Gate E is run and recorded — the issue-solver rules call this out by name as expected, not a regression |

## Proxy overlap (NOT Gate E)

Spearman rho of each `EWMAC_*` column against `MACD_12_26_9 / close * 100` (the issue's own
"roughly `MACD_pct / natr` at 12/26" guess, nearest comparator by construction) and
`NATR_14`, on one synthetic tick-rounded GBM walk (sigma=0.02, seed 11, tick 0.05, n=1,200;
`natr`'s high/low are `close * 1.001` / `close * 0.999`, a cheap synthetic substitute, not
real OHLC):

| column | rho vs `MACD_pct(12,26)` | rho vs `NATR_14` | n |
|---|---|---|---|
| `EWMAC_2_8_35` | 0.4503 | -0.1621 | 1,175 |
| `EWMAC_4_16_35` | 0.7963 | -0.2041 | 1,175 |
| `EWMAC_8_32_35` | 0.9927 | -0.2478 | 1,175 |
| `EWMAC_16_64_35` | 0.8616 | -0.2761 | 1,175 |
| `EWMAC_32_128_35` | 0.4945 | -0.2372 | 1,175 |
| `EWMAC_64_256_35` | 0.1360 | -0.1560 | 1,175 |

This is directionally consistent with the issue's own pre-registered expectation: the
fast/medium pairs (`8_32` especially, at 0.9927, close to `MACD`'s own 12:26 speed) look
likely to collide with the engine's MACD family on real Gate E; the slow pairs (`32_128`,
`64_256`) are far lower here. This is **not** Gate E — one synthetic walk against two
guessed comparators, not 89 BIST frames against 687 — and gives no information about
`PPO` or `MACD_Hist_ATR`, which need real OHLC the synthetic walk does not have a genuine
version of. The real Gate E run decides which, if any, of the six columns ship.

## To close

1. Run `gate_e_overlap.py run --module pandas_ta.momentum.ewmac` (launcher) and record each
   column's pooled max |rho| and per-frame max median |rho| here, then record the row in
   `docs/gate_e_ledger.csv`.
2. Apply CLAUDE.md's bands per column (STRUCK / DISCLOSE_GAP / DISCLOSE / SHIP). Any
   column STRUCK gets reverted individually (the six are independent columns from one
   module, not a package deal) unless waived; a waiver needs the owner's decision.
3. Fill Gate C from the same real frames (reachability counts on real BIST data).
4. Regenerate `docs/IndicatorDictionary.md` if any column is reverted.
5. Run both suites.
