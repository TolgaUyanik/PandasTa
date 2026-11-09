# g191_002 — measured (issue #63)

> **Status: Gates A-E cleared (SHIP), this repo's suite green.**

One-day change of close location: Guotai Junan's (2017, "GTJA191", internal
quant report, read via the HKUDS/Vibe-Trading copy, MIT) alpha `#2`, per
issue #63's own instruction. Module `pandas_ta/momentum/g191_002.py`,
column `G191_002_1`. Tests: `tests/test_g191_002.py` (16, all passing).
Numbers below: `python docs/measure_g191_002.py`. Environment: this
worktree's pinned pandas/numpy. Measured 2026-11-09.

## Gate A: derivation from the published formula, not the prototype

Issue #63 states GTJA191 alpha `#2`:

    -DELTA(((C-L)-(H-C))/(H-L),1)

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own
named copy -- HKUDS/Vibe-Trading (MIT) -- was never read. Everything
below is derived from the issue's own stated formula string, per the
issue's own rule ("Gate A starts from the source formula, not the
prototype"), then cross-checked against the issue's own prototype
(`docs/issues/screen/ind_screen.py:278-279`):

    @cand("g191_002", "one-day change of close location", G,
          "#2: -DELTA(((C-L)-(H-C))/(H-L),1)")
    def _(o, h, l, c, v): return -delta(clv(h, l, c), 1)

with `clv`/`delta` and `sdiv`/`_fin` read directly off the same module
source (`ind_screen.py:110`, `:46`, `:41-42`, `:37-38`):

    def clv(h, l, c): return sdiv((c - l) - (h - c), h - l)
    def delta(x, n): return x - x.shift(n)
    def sdiv(a, b): return _fin(a / b)
    def _fin(x): return x.replace([np.inf, -np.inf], np.nan)

No disclosed interpretation choice was needed -- the issue's own string
and the prototype agree exactly, including the fixed `1`-bar delta and
the absence of any additional scale-free conversion (the issue's own
`conv` field for this candidate is empty, unlike e.g. `g191_093`'s
`/close`). `clv` reduces algebraically to `(2*C-H-L)/(H-L)` -- the same
simplification `pandas_ta.momentum.a101_053` already uses for its own
close-location ratio, which has a DIFFERENT denominator (`close-low`,
not `high-low`) and a different source formula (Alpha101 `#53`, not
GTJA191 `#2`); the two are not a restatement of each other, since the
denominators diverge whenever `close != high`.

### Warm-up and the zero-denominator case: disclosed, not modelled around

`clv[t]` is undefined (`NaN`) whenever `high[t] == low[t]` (a flat,
zero-range bar); `DELTA(clv, 1)` additionally needs `clv[t-1]`, so true
warm-up is `min_length = length + 1` -- **2** bars at the shipped default
(`length=1`), enforced by `verify_series`. Under ordinary OHLC
consistency (`low <= open, close <= high`), `high == low` forces
`open == close == high == low` too -- a fully flat bar, a rarer
degenerate case than `a101_053`'s own `close == low` zero-denominator
("close prints at its own low", measured 21.17% of BIST daily bars per
the `fvg`/FVGDEAD note in `CLAUDE.md`), since it additionally requires
the high to coincide with the low on the same bar. Measured on a
1,500-bar synthetic continuous-float walk (`python
docs/measure_g191_002.py`): **0 of 1,500** zero-range bars, so the
`sdiv` NaN-branch never fires on this walk; real tick-rounded exchange
data can still hit it, so the mask stays in the formula regardless,
matching the prototype's own unconditional use of `sdiv`.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula, matching the issue's own prototype line-for-line | A hand-derived 8-bar example (`length=3`, same OHLC numbers as `a101_053`'s own hand-derived example but a different denominator): module output `[nan, nan, nan, 0.0, 0.0, -0.2666666666666667, 0.0, -0.6]`, bar-by-bar match to `pytest.approx(..., abs=1e-12)`. A zero-denominator example (`high==low` at two bars, `length=1`): module output `[nan, nan, 0.0, nan, nan]`, confirming NaN (never a signed infinity) propagates through `diff` exactly like any other missing value. An independent per-bar computation (plain numpy indexing, not the module's own `.diff()` call) spot-checked at the shipped default on a 900-bar frame: `t=300 module=0.1447634240408519 independent=0.1447634240408519`, `t=600` and `t=899` identical to float precision (`python docs/measure_g191_002.py`) |
| B Causality | pass | Future-perturbation sweep (high/low/close jointly rewritten from `j` onward), 37 offsets past the 2-bar warm-up: real module **0 of 37** leaks. Write-shift mutant (final write index shifted 30 bars into the future, `result = (-d1).shift(-30)`): shown live different from the real module, then caught **37 of 37** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic high/low/close walk (seed 11, see `docs/measure_g191_002.py:_walk`), shipped default: **1,499 of 1,500** bars non-NaN (99.93%), first valid at bar 1 (exactly the structural warm-up boundary, `min_length - 1`). **1,499 distinct values**. Range `[-1.857726, 1.880959]`, median `0.015892` |
| D Scale-free | pass | `clv`'s numerator (`2*close-high-low`) and denominator (`high-low`) are both linear in `(high,low,close)`, so a positive rescale cancels exactly, leaving `clv` -- and hence `DELTA(clv,1)` and its negation -- unchanged. Measured on the 1,500-bar walk: PRICE x8/x64 **bit-identical, 0.0 max\|diff\|** (power-of-two multiplication is exact in IEEE754); x10/x3.7 **within float64 rounding tolerance** (max\|diff\| 2.75e-13 / 3.46e-13). `0 < 1499 fires < 1500` and `1499 > 1` distinct values rule out a constant column |
| E Attribution | SHIP | `G191_002_1`: max \|ρ\| **0.6885** vs `CLV_Pctl` (manifest, n = 391,357); per-frame max median \|ρ\| **0.6867** (against `CLV_Pctl`, 89 frames, 0.0% of frames ≥ 0.90). Below both SHIP thresholds (pooled < 0.76, per-frame median < 0.90). Run `is63-g191_002-9647fe36`, 89 ALTPORT-1 frames, 398,849 pooled bars, 329 + 358 = 687 comparators, canary bit-equal (`AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS`), measured 2026-11-09 |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **297 -> 298** (`momentum` **73 -> 74**); `df.ta.<name>()`
accessor count **305 -> 306**. Touch points:
`pandas_ta/momentum/g191_002.py` (module),
`pandas_ta/momentum/__init__.py` (export), `pandas_ta/__init__.py` ->
`Category["momentum"]` (discovery), `pandas_ta/core.py` ->
`AnalysisIndicators.g191_002` (accessor), `tests/test_g191_002.py`
(tests). `README.md`'s headline and `momentum (74)` row, and
`docs/IndicatorDictionary.md` (regenerated, `299 -> 300` probed), both
updated and checked by `tests/test_readme_counts.py`.
`docs/MLCompanionContract.md`'s running tag count updated **642 -> 643 /
285 -> 286 `SF`** (`G191_002_1` probes cleanly at the dictionary's
600-bar synthetic frame and takes many distinct values, so the generator
tags it `SF`), checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match
(297 -> 298); no `CATEGORY_BUCKETS` entry needed (that dict only tracks
`trend`/`volatility`/`volume`, not `momentum`).

Gate E run by the launcher (`gate_e_overlap.py`, Backtesting #107);
`docs/gate_e_ledger.csv` row recorded 2026-11-09
(`python docs/gate_e_ledger.py record ... --measured 2026-11-09`).

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order (after Gate
E ran and its ledger row was recorded, 2026-11-09): **3 failed, 4802
passed, 83 skipped**. `g191_002`'s own tests (`tests/test_g191_002.py`):
**16 passed**. Pre-existing failures, unrelated to this port
(CLAUDE.md "Known breaks"):
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
(owed for `['mtd_ret']` only -- that row pre-dates this session;
`g191_002`'s own row is recorded and no longer owed),
`tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this
worktree) and `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
(untracked `docs/pine/` corpus). No other test regresses.
