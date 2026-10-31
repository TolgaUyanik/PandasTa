# Range volatility trio — measured (`garman_klass`, `rogers_satchell`, `yang_zhang`)

Issue #17 (RANGEVOL), found by the ResearchIntel RAG scan of 2026-10-22. Three OHLC range
volatility estimators, more statistically efficient than a close-to-close standard deviation
because each also uses the bar's own high/low (and, for Yang-Zhang, the overnight open):
Garman & Klass (1980), Rogers & Satchell (1991, drift-independent by construction), and
Yang & Zhang (2000, adds the overnight close-to-open jump on top of Rogers-Satchell).

**Status: Gates A-D cleared; wired into `Category`. Gate E: pending, run by issue-solver
after this session.** The issue pre-registers an expectation of revert, guessing max |rho|
>= 0.9 against `natr` / `har_park` (the fork's existing range-volatility columns). **On the
synthetic proxy below, that guess does NOT hold**: the measured max against `natr` /
`har_park` is **0.6389** (`YZVOL_20` vs `NATR_14`), well under 0.9 and even under the
DISCLOSE band (0.76). A synthetic proxy is not Gate E, and Gate E over the real 89-frame
BIST set is the measurement the protocol actually decides on (`r3-perframe-0.90`); it has
not run yet (this session may not touch the Backtesting repo). **This file does not make
the ship/revert call** -- the receipt session that records Gate E does, per CLAUDE.md and
the measured-revert precedent in `docs/DicksonMaMeasured.md` / `docs/KalmanTrendMeasured.md`.

Shipped as **three modules** (CLAUDE.md's "one indicator, one module" -- three independent
papers, like the Liquidity trio in `docs/LiquidityMeasured.md`, not three facets of one
computation), using exactly this session's 3-new-file allowance, all three in `volatility`
next to `har_park` (the fork's other price-only range estimator):

| module | column | range (synthetic, n=1200 seed=11) |
|---|---|---|
| `pandas_ta/volatility/garman_klass.py` | `GKVOL_20` | `[0.6968, 1.3573]` (percent) |
| `pandas_ta/volatility/rogers_satchell.py` | `RSVOL_20` | `[0.6153, 1.2672]` (percent) |
| `pandas_ta/volatility/yang_zhang.py` | `YZVOL_20` | `[0.8080, 1.3786]` (percent) |

Tests: `tests/test_garman_klass.py` (13), `tests/test_rogers_satchell.py` (13),
`tests/test_yang_zhang.py` (15). Numbers: `python docs/measure_rangevol.py`. Environment:
pandas 2.3.3, numpy 1.26.4, Python 3.11.2. Measured 2026-10-31.

## Sources, and how far each was checked

| source | used for | how it is known |
|---|---|---|
| Aldridge, "High-Frequency Trading" (2010), ch. 8 and ch. 10 | that Garman-Klass is discussed as an execution/risk-sizing volatility estimator | the issue text; **not available on this machine, not fetched** |
| Garman, M. and Klass, M. (1980), "On the Estimation of Security Price Volatilities from Historical Data", Journal of Business 53(1) | the Garman-Klass formula | the commonly reproduced closed form; **not fetched**, not checked line by line against the original paper |
| Rogers, L.C.G. and Satchell, S.E. (1991), "Estimating Variance From High, Low and Closing Prices", Annals of Applied Probability 1(4) | the Rogers-Satchell formula | the commonly reproduced closed form; **not fetched** |
| Kissell, "The Science of Algorithmic Trading and Portfolio Management" (2013), ch. 13 | that Yang-Zhang is discussed in an algo-trading execution context | the issue text; **not available on this machine, not fetched** |
| Isichenko, "Quantitative Portfolio Management" (2021), ch. 2 | same, portfolio-management context | the issue text; **not available on this machine, not fetched** |
| Yang, D. and Zhang, Q. (2000), "Drift Independent Volatility Estimation Based on High, Low, Open, and Close Prices", Journal of Business 73(3) | the Yang-Zhang formula and its bias-correction weight `k` | the commonly reproduced closed form; **not fetched** |

None of the six sources were read for this port. Gate A below is therefore an algebraic
derivation and an independent reimplementation of the commonly-published formulas, not a
line-by-line citation check against any of them -- unlike the Pine-porting protocol, there
is no source file to cite line numbers from.

## Decisions (explicit, since none of the sources were read)

1. **Not annualised.** Reported as a rolling RMS volatility in percent (`100 * sqrt(mean
   variance))`), matching `har_park`'s `park_pct` convention, rather than imposing a
   `sqrt(252)`-style trading-day assumption this repo's single-asset frames cannot justify
   on their own (a weekly or monthly-bar frame would need a different annualisation factor).
2. **`length=20` default for all three**, independent of each paper's own convention (none
   of which was read) -- for consistency with this repo's `natr`/`kc`/`donchian` 20-bar
   convention. `yang_zhang` additionally requires `length > 1` (division by `length - 1` in
   its bias weight `k`); a caller-supplied 0 or 1 falls back to 20, matching `gapm`'s and
   `corwin_schultz`'s length guards rather than raising.
3. **A malformed bar (`high < max(open, close))` or non-positive price) is masked to NaN**,
   matching `corwin_schultz`'s `_valid_bar` precedent, rather than trusted. Every window
   touching a masked bar reads NaN and recovers once the window clears it (pinned by a test
   per module).
4. **The `clip(lower=0.0)` before each `sqrt` is float-safety only, not a correctness fix.**
   Unlike `corwin_schultz`'s alpha clip (which engages on 46-86% of bars and changes the
   value), Garman-Klass's and Rogers-Satchell's per-bar terms are proved algebraically
   non-negative whenever `high >= max(open, close)` and `low <= min(open, close)` (module
   docstrings) -- and Yang-Zhang's combined variance is a sum of two sample variances (>= 0
   by construction) and a non-negative weight times the (also non-negative) Rogers-Satchell
   mean. **Measured** (`docs/measure_rangevol.py`, clip-engagement section): on the 1,200-bar
   synthetic fixture the raw per-bar terms' minimum is `7.01e-08` (Garman-Klass) and exactly
   `0.0` (Rogers-Satchell), with **zero** bars below zero in either -- the clip never
   actually engaged on this data. It stays in the code as a guard against float cancellation
   on a near-degenerate bar (e.g. a near-zero-range, near-zero-wick bar), not because it was
   observed to fire.
5. **`garman_klass`/`rogers_satchell` are self-contained, not built on top of each other**,
   even though Yang-Zhang's own formula embeds the Rogers-Satchell term. Each module repeats
   the small `_valid_ohlc` helper rather than importing from a sibling -- matching
   `corwin_schultz`'s own `_valid_bar`/`_hl2` precedent of per-module helpers, and the
   session's file-count limit does not allow a fourth shared-helper module.

## Open-quality disclosure (issue #14, applies to `yang_zhang` only)

`yang_zhang` is the one of the three that reads `open` (via the overnight close-to-open
return), so issue #14's risk applies: Quantpedia's warning that a free OHLC feed's `open` is
often unreliable, e.g. `open == prior close` on many bars. **Measured on SYNTHETIC data
only** (`docs/measure_rangevol.py`, open-quality section) -- the real-data rate is NOT
measured here, same gap as #14 itself, which is still backlog:

| p (forced overnight==0 in the generator) | measured open==prior_close fraction (post-tick-rounding) | YZVOL_20 fires | YZVOL_20 range |
|---|---|---|---|
| 0.0 | 0.0033 | 1180/1200 | [0.8080, 1.3786] |
| 0.5 | 0.5129 | 1180/1200 | [0.7206, 1.3565] |
| 0.8 | 0.8140 | 1180/1200 | [0.7007, 1.3256] |
| 0.9 | 0.8999 | 1180/1200 | [0.6878, 1.2990] |

`YZVOL_20` keeps firing at the same rate regardless of `p` -- a flat overnight return is a
valid (zero) sample for the rolling sample variance, not a NaN-producing edge case like
`gapm`'s zero-denominator. As `p` rises, the overnight variance term shrinks toward 0 and
the column leans more on the Rogers-Satchell term, which is visible as a narrowing range
(max drops from 1.3786 to 1.2990 as `p` goes from 0 to 0.9) but not as any NaN or exception.
**Real BIST open-quality is unmeasured; if issue #14 ever measures it, re-check this table
against the real rate.**

## Mutual redundancy among the three (disclosed, not resolved here)

Not asked for by the gates, but visible in the same proxy run and worth recording: on the
3,000-bar proxy walk below, the three new columns correlate heavily **with each other**
(Spearman rho, n~2,980): `GKVOL_20` vs `RSVOL_20` **0.9833**, `GKVOL_20` vs `YZVOL_20`
**0.9695**, `RSVOL_20` vs `YZVOL_20` **0.9423** -- all three measure the same bars' range,
so this is expected, not a bug. CLAUDE.md's non-redundancy rule is about restating an
*already-shipped* column, which this is not, but if Gate E ships more than one of the three,
a later reviewer should know they are near-duplicates of each other, not independent
signals, before trusting a tree that picks up more than one.

## Gates

Synthetic numbers come from `docs/measure_rangevol.py` and the three test modules (1,200-bar
tick walk, seed 11, for Gate C/D; 3,000-bar walk, seed 1, for the proxy overlap).

| Gate | Result |
|---|---|
| A Correctness | **Against the commonly-published formulas only; none of the six sources were fetched (see above).** `garman_klass`: two hand-derived closed forms (a pure-wick bar isolating the HL term, a monotonic no-wick bar isolating the OC term) plus an independent per-bar loop at four interior bars of a synthetic walk. `rogers_satchell`: a hand-derived monotonic no-wick bar reading exactly 0, a hand-derived pure-wick bar, plus the same independent-loop check. `yang_zhang`: a hand-derived flat-market closed form (every log-ratio is `ln(1)=0`, so `YZVOL==0` exactly) plus an independent per-bar loop using a manually-coded rolling sample variance (not `.rolling().var()`) at three interior bars. All three additionally tested for a malformed bar (NaN, with recovery once the window clears it) and a length-guard edge case (`yang_zhang`'s `length=1` falls back to the default rather than raising `ZeroDivisionError`). |
| B Causality | Future-perturbation sweep (31 offsets for `garman_klass`/`rogers_satchell`, 30 for `yang_zhang` since its warm-up is one bar longer; the real module leaks at 0/31 or 0/30 for all three) plus one `importlib`-read, `exec`'d-in-memory look-ahead mutant per module: `garman_klass`/`rogers_satchell` shift the rolling input one bar into the future (`per_bar.shift(-1)`); `yang_zhang` reads the NEXT bar's close as "prior close" (`close.shift(-1)` instead of `close.shift(1)`). Each mutant is proved live (differs from the real module), then measured: **caught at 31/31** (`garman_klass`), **31/31** (`rogers_satchell`), **30/30** (`yang_zhang`) -- every mutant is caught at every perturbation offset tested. |
| C Reachability | Synthetic only (real-data counts owed to the Gate E receipt session, same gap as every pending-Gate-E port in this repo): `GKVOL_20`/`RSVOL_20` fire 1,181/1,200 (1,181 distinct), `YZVOL_20` fires 1,180/1,200 (1,180 distinct, one bar shorter warm-up margin from needing `length+1` bars for the overnight term). |
| D Scale-free | All three: x8/x64 bit-identical (`max|diff| = 0.0`, NaN masks matching -- every term is a log-ratio of prices, exact under a power-of-two rescale); x10/x3.7 within `9.10e-15`/`8.44e-15` (`GKVOL_20`), `1.27e-14`/`8.66e-15` (`RSVOL_20`), `7.99e-15`/`6.00e-15` (`YZVOL_20`). `0 < fires < n` plus > 100 distinct values, all three (measured: 1,181 / 1,181 / 1,180 distinct, well over 100). |
| E Attribution | **Pending, run by issue-solver after this session.** Bands `r3-perframe-0.90`, 89 ALTPORT-1 frames, 687 comparators (329 `compute_all` + 358 manifest `1d`), per CLAUDE.md's Gate E harness. The pre-registered guess (max |rho| >= 0.9 vs `natr`/`har_park`) is NOT supported by the synthetic proxy below; Gate E on real data is what decides. |
| F Suites | This repo only (parent repo run by the launcher): `python -m pytest -q`, 2026-10-31, this tree: **3 failed / 3,544 passed / 83 skipped** -- exactly the two pre-existing CLAUDE.md known breaks (`test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`, `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`) plus `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (expected -- no ledger row yet, per this session's instructions: Gate E has not run). Nothing else fails; the README/dictionary/companion-count/category-count tests are green against this session's own edits (`README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py`). |

## Proxy overlap (NOT Gate E)

Spearman rho on one synthetic 3,000-bar walk (seed 1, overnight sigma 0.004, intraday sigma
0.012, tick 0.01), n ~ 2,980-2,981:

| column | vs `NATR_14` | vs `HARPARK_1_5_22_500` | vs `TRUE_RANGE` (% of close) | vs `RVI_14` |
|---|---|---|---|---|
| `GKVOL_20` | 0.6203 | -0.0128 | 0.1574 | -0.0371 |
| `RSVOL_20` | 0.5576 | -0.0201 | 0.1404 | -0.0444 |
| `YZVOL_20` | **0.6389** | 0.0118 | 0.1686 | -0.0240 |

The issue's pre-registered guess was max |rho| >= 0.9 against `natr`/`har_park`. The
measured max here is 0.6389 (`YZVOL_20` vs `NATR_14`), under even the DISCLOSE band (0.76).
`har_park`'s near-zero correlation with all three is plausible rather than suspicious: it is
a one-bar-ahead HAR-regression FORECAST of Parkinson volatility, not a realised-volatility
level, so the forecasting/lag transformation is expected to decorrelate it from a same-bar
range estimator -- this is read off the numbers, not independently re-derived.

This is a synthetic single-walk proxy, not Gate E: the real engine's 687 comparators over 89
BIST frames (`compute_all` plus the `ml_features` manifest) may differ, and that is the
measurement the protocol actually bands against.

## To close

1. Launcher runs Gate E (`gate_e_overlap.py run --module pandas_ta.volatility.garman_klass`
   / `.rogers_satchell` / `.yang_zhang`) against the 89 ALTPORT-1 frames.
2. A receipt session reads the launcher's output, enters the measured max |rho| per column
   (pooled and per-frame-median) with its comparator and sample size above, and records the
   `docs/gate_e_ledger.csv` rows (`python docs/gate_e_ledger.py record`).
3. Apply CLAUDE.md's `r3-perframe-0.90` bands per column. A column that STRUCKs is deleted
   (module, export, `Category` entry, accessor, test file, README/dictionary/contract/
   `test_altport2_ports.py` counts) and this file is kept as the receipt for that column; a
   column that ships keeps everything as committed here. Given the mutual-redundancy numbers
   above, more than one column may clear Gate E individually while still being redundant with
   each other -- worth a second look before keeping all three.
4. Run both suites again after any revert.
