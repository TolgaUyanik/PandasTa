# g191_189 — measured (issue #61)

> **Status: Gates A-F cleared. SHIP.**

Mean absolute deviation from the 6-day mean: Guotai Junan's (2017,
"GTJA191", internal quant report, read via the HKUDS/Vibe-Trading copy,
MIT) alpha `#189`, per issue #61's own instruction. Module
`pandas_ta/statistics/g191_189.py`, column `G191_189_6_6`. Tests:
`tests/test_g191_189.py` (20, all passing). Numbers below:
`python docs/measure_g191_189.py`. Environment: this worktree's pinned
pandas/numpy. Measured 2026-11-09.

## Gate A: derivation from the published formula, not the prototype

Issue #61 states GTJA191 alpha `#189`:

    MEAN(|C-MEAN(C,6)|,6)

with the issue's own stated scale-free form: "`/close`".

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own
named copy -- HKUDS/Vibe-Trading (MIT) -- was never read. Everything below
is derived from the issue's own stated formula string plus its own
scale-free instruction, per the issue's own rule ("Gate A starts from the
source formula, not the prototype"), then cross-checked against the
issue's own prototype (`docs/issues/screen/ind_screen.py:566-567`):

    @cand("g191_189", "mean absolute deviation from the 6-day mean", G,
          "#189: MEAN(|C-MEAN(C,6)|,6)", "/close")
    def _(o, h, l, c, v): return mean((c - mean(c, 6)).abs(), 6) / c

No disclosed interpretation choice was needed -- the issue's own string and
the prototype agree exactly, including both window lengths and the
scale-free conversion. Operators, each read directly off the prototype's
own module source (`ind_screen.py:47`): `MEAN(X,n) = X.rolling(n).mean()`,
matching the convention every other `g191_*` port in this fork already
relies on.

### Non-redundancy with the already-shipped `mad` indicator

`pandas_ta/statistics/mad.py` also computes "mean absolute deviation", so
this was checked explicitly rather than assumed: `mad(close, length)`
computes ONE window mean per trailing window and averages deviations from
that single shared mean. `G191_189` instead builds a full rolling-mean
SERIES first, takes the per-bar deviation from each bar's own LOCAL mean,
and averages those -- a genuinely different statistic, not a renamed
duplicate. Measured on a 300-bar trending synthetic series
(`mean_length=mad_length=6` vs. `mad(close,6)`, both divided by `close` to
compare on the same footing): **290 of 290** overlapping non-NaN bars
disagree (`python docs/measure_g191_189.py`), confirmed by
`tests/test_g191_189.py::test_differs_from_the_shipped_mad_indicator`.
The two formulas coincide only in the FULLY degenerate case
`mean_length=mad_length=1` (both collapse to an identically-zero column,
`close[t]-close[t]=0`); at `mad_length=1` ALONE with `mean_length=3` they
still disagree -- measured on `close=[1,2,3,4,5]`: `mad.py` reads
`0.666667` at every one of 3 checked bars, `g191_189`'s pre-division
deviation reads `1.0` at the same bars (`python docs/measure_g191_189.py`),
confirmed by `tests/test_g191_189.py::test_still_differs_from_mad_at_mad_length_one`.
A validation bug was caught and fixed while measuring this: the original
argument guards used `mean_length > 1` / `mad_length > 1`, which silently
fell back to the default `6` for the legitimate value `1` instead of
honouring it -- pinned by
`tests/test_g191_189.py::test_length_one_is_honoured_not_silently_defaulted`.

### Warm-up: a disclosed necessary condition

`inner_mean` needs `mean_length` bars; `mad` (the outer rolling mean) needs
`mad_length` CONSECUTIVE valid `inner_mean`-derived deviations. True
warm-up: `min_length = mean_length + mad_length - 1` -- **11** at the
shipped defaults (`mean_length=6, mad_length=6`), enforced by
`verify_series`.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula plus its own scale-free conversion, matching the issue's own prototype line-for-line | Spot-checked against an independent per-bar computation (plain python loop re-deriving the nested rolling mean from scratch, not the module's own vectorised `.rolling()` calls), both at small lengths (`mean_length=3, mad_length=2`, 3 bars on a 60-bar frame) and at the shipped defaults (3 bars on a 300-bar frame), plus a fully hand-computed window: every spot-checked bar matches the module's float64 output exactly or to float rounding, e.g. `t=200 module=0.012252695453080895 independent=0.012252695453080895`, `t=299 module=0.011472614551164701 independent=0.01147261455116473` (`python docs/measure_g191_189.py`) |
| B Causality | pass | Future-perturbation sweep (close series rewritten from `j` onward, another synthetic frame), 22 offsets past the 11-bar warm-up: real module **0 of 22** leaks (`python docs/measure_g191_189.py`). One mutant (`importlib` source read, `exec`'d in memory, shown live-different from the real module): shifting the final rolling-mean write index `mad_length=6` bars into the future -- caught at **22 of 22** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 900-bar synthetic close series (seed 11, see `docs/measure_g191_189.py:_close`), shipped default: **890 of 900** bars non-NaN (98.89%), first valid at bar 10 (exactly the structural warm-up boundary, `min_length - 1`). **890 distinct values** (continuous statistic, no inherent ceiling unlike a rank-based column). Range `[0.002574, 0.041536]`, median `0.013310` |
| D Scale-free | pass | `inner_mean` is linear in `close`, so a positive rescale `k*close` scales it to `k*inner_mean`; `deviation = |close - inner_mean|` then scales to `k*deviation`; `mad` (a plain average) scales to `k*mad`; dividing by `k*close` cancels the `k` exactly. Measured on the 900-bar series: PRICE x8/x64 **bit-identical, 0.0 max\|diff\|** (power-of-two multiplication is exact in IEEE754); x10/x3.7 **within float64 rounding tolerance** (max\|diff\| 1.7e-16 / 1.5e-16 -- the rolling-mean and division arithmetic itself rounds differently at a non-power-of-two multiplier, even though the true ratio is identical). `0 < 890 fires < 900` and `890 > 1` distinct values rule out a constant column |
| E Attribution | SHIP | `G191_189_6_6`: max\|rho\| 0.6726427263356 vs `natr` (`compute_all`, n = 397,692); per-frame max median 0.6572564719700037 (89 frames); verdict SHIP (< 0.76 ship line). Run `is61-g191_189-0f5bacef`, 89 ALTPORT-1 frames, 398,849 pooled bars, 329 + 358 comparators, canary bit-equal (`AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS`). Measured 2026-11-09, ledger row recorded in `docs/gate_e_ledger.csv` |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **295 -> 296** (`statistics` **27 -> 28**); `df.ta.<name>()`
accessor count **303 -> 304**. Touch points:
`pandas_ta/statistics/g191_189.py` (module),
`pandas_ta/statistics/__init__.py` (export), `pandas_ta/__init__.py` ->
`Category["statistics"]` (discovery), `pandas_ta/core.py` ->
`AnalysisIndicators.g191_189` (accessor), `tests/test_g191_189.py`
(tests). `README.md`'s headline and `statistics (28)` row, and
`docs/IndicatorDictionary.md` (regenerated, `297 -> 298` probed), both
updated and checked by `tests/test_readme_counts.py`.
`docs/MLCompanionContract.md`'s running tag count updated **640 -> 641 /
283 -> 284 `SF`** (`G191_189_6_6` probes cleanly at the dictionary's
600-bar synthetic frame and takes many distinct values, so the generator
tags it `SF`), checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match
(295 -> 296); no `CATEGORY_BUCKETS` entry needed (that dict only tracks
`trend`/`volatility`/`volume`, not `statistics`).

Gate E run by the launcher (`gate_e_overlap.py`, Backtesting #107);
ledger row recorded above, 2026-11-09.

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order: **3 failed,
4747 passed, 83 skipped**. `g191_189`'s own tests (`tests/test_g191_189.py`):
**20 passed**. Pre-existing / expected failures, all unrelated to this
port's correctness (CLAUDE.md "Known breaks" plus this port's own owed
Gate E row):
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
(owed for `['g191_189', 'mtd_ret']` -- `g191_189`'s row is owed by design
per this session's override rules; `mtd_ret` pre-dates this session),
`tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this
worktree) and `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
(untracked `docs/pine/` corpus). No other test regresses.
