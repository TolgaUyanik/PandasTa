# g191_109 — measured (issue #76)

> **Status: Gates A-D cleared. Gate E: pending, run by issue-solver after this session.
> This repo's suite green except the pre-existing breaks below and the owed Gate E ledger row.**

Range EMA over its own EMA (single mass-index ratio): Guotai Junan's (2017, "GTJA191",
internal quant report, read via the HKUDS/Vibe-Trading copy, MIT) alpha `#109`, per issue #76's
own instruction. Module `pandas_ta/volatility/g191_109.py`, column `G191_109_10_2_10_2`. Tests:
`tests/test_g191_109.py` (17, all passing). Numbers below: `python docs/measure_g191_109.py`.
Environment: this worktree's pinned pandas/numpy, per `docs/IndicatorDictionary.md`'s header.
Measured 2026-11-10.

## Gate A: derivation from the published formula, not the prototype

Issue #76 states GTJA191 alpha `#109`:

    SMA(H-L,10,2) / SMA(SMA(H-L,10,2),10,2)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web access are both
unavailable in this worktree, so the issue's own named copy -- HKUDS/Vibe-Trading (MIT) -- was
never read. Everything below is derived from the issue's own stated formula string, per the
issue's own rule ("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype (`docs/issues/screen/ind_screen.py:452-456`):

    @cand("g191_109", "range EMA over its own EMA (single mass-index ratio)", G,
          "#109: SMA(H-L,10,2) / SMA(SMA(H-L,10,2),10,2)")
    def _(o, h, l, c, v):
        e = sma(h - l, 10, 2)
        return sdiv(e, sma(e, 10, 2))

No disclosed interpretation choice was needed -- the issue's own string and the prototype
agree exactly, including both window lengths/weights. Unlike every other ratio-form `g191_*`
port in this fork (`g191_023`, `g191_111`, ...), this candidate's own `candidates.csv` row
carries NO `conv` field (an empty cell, `docs/issues/screen/candidates.csv:46`) -- there is no
extra scale-free conversion to apply, because the ratio of a quantity to its OWN recursive
smoothing is already scale-free by construction (derived below).

Operators, each read directly off the prototype's own module source: `H`, `L` = high, low (no
other OHLCV field is read), and `SMA(A,n,m)` -- NOT this fork's plain simple-moving-average
`sma` but GTJA's own recursive smoother, called out explicitly in the prototype's own docstring
(`ind_screen.py:57-59`): `Y[t] = (m*A[t] + (n-m)*Y[t-1])/n`, an EMA with `alpha = m/n`. The same
operator and the same `ewm(alpha=m/n, adjust=False, min_periods=n)` implementation already
ships in every sibling `g191_*` port for the identical GTJA `SMA` operator, applied here TWICE
in a CHAIN (the second application smooths the OUTPUT of the first), unlike `g191_111`'s two
`SMA`s applied in PARALLEL to the same input series. The prototype's own `sdiv`
(`ind_screen.py:41-42`, `_fin(a / b)`) replaces `+-inf` with `NaN` on the final division.

### The structure: a quantity over its own further smoothing

`e = SMA(H-L, 10, 2)` is the GTJA-smoothed daily range. `s = SMA(e, 10, 2)` smooths `e` AGAIN
with the same recursion. The result `e/s` is a mass-index-style oscillator: it rises above 1
when the range is expanding faster than its own trailing average, and falls below 1 when it is
contracting. Because both `e` and `s` are built from the SAME underlying series by the SAME
linear operator, a price rescale cancels between them with no extra division needed -- the
structural reason the issue's own `candidates.csv` row carries no `conv` field.

### Warm-up: a disclosed necessary condition

`e = SMA(H-L, smooth1_length, smooth1_weight)` needs `smooth1_length` valid `(H-L)` values
(`min_periods=10`); ordinary OHLC data never produces a NaN range (`H-L=0` on a tie is still a
valid float), so `e` is defined from `t >= smooth1_length - 1`. `s = SMA(e, smooth2_length,
smooth2_weight)` is itself an SMA OF `e`, so it needs `smooth2_length` valid `e` values AFTER
`e` starts. Total: `min_length = smooth1_length + smooth2_length - 1` = `10+10-1` = **19** bars
at the shipped defaults, enforced by `verify_series` -- the same chained-smoother warm-up
arithmetic `g191_174` uses for its STD-then-SMA chain.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula, matching the issue's own prototype line-for-line | An 8-bar hand-derived example (`smooth1_length=3, smooth1_weight=1, smooth2_length=2, smooth2_weight=1`) checked against an independent computation of the chained GTJA `SMA` (`python docs/measure_g191_109.py`), matching the module's float64 output exactly at bars 3-7, plus an independent per-bar loop (plain numpy, not the module's own `.rolling()`/`.ewm()` calls) spot-checked at the shipped defaults on a 900-bar frame at bars 300/600/899 (bit-identical, diff 0.000e+00) |
| B Causality | pass | Future-perturbation sweep (high/low series rewritten from `j` onward), 37 offsets past the 19-bar warm-up: real module **0 of 37** leaks. Write-shift mutant (final write index `smooth2_length=10` bars into the future): caught **37 of 37**. Look-ahead-range mutant (`e` computed from `high.shift(-1) - low.shift(-1)`, one bar of look-ahead folded into the range before smoothing, the `bos` look-ahead bug class): caught **37 of 37** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic high/low series (seed 11, lognormal walk, `docs/measure_g191_109.py:_walk`), shipped default: **1,482 of 1,500** bars non-NaN (98.80%), first valid at bar 18 (exactly the structural warm-up boundary, `min_length - 1`). **1,482 distinct values**. Range `[0.753181, 1.324601]`, median `0.998151`, no negative values observed |
| D Scale-free | pass | `H-L` is linear in a positive price rescale, and the GTJA `SMA` recursion is linear in a positive scalar multiple of its input, so BOTH `e` and `s` scale by the SAME factor and the ratio `e/s` cancels it exactly, with no extra division needed. Measured on the 1,500-bar series: PRICE x8/x64 **bit-identical, 0.0 max\|diff\|** (power-of-two multiplication is exact in IEEE754); x10/x3.7 **within float64 rounding tolerance** (max\|diff\| 4.55e-15 / 3.00e-15). `0 < 1482 fires < 1500` and `1482 > 1` distinct values rule out a constant column; no negative value observed on the fired bars |
| E Attribution | **pending, run by issue-solver after this session** | per CLAUDE.md "Owed, not failed" -- this session does not run Gate E or touch `../Backtesting` |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **310 -> 311** (`volatility` **31 -> 32**); `df.ta.<name>()` accessor count **318 ->
319**. Touch points: `pandas_ta/volatility/g191_109.py` (module),
`pandas_ta/volatility/__init__.py` (export), `pandas_ta/__init__.py` -> `Category["volatility"]`
(discovery), `pandas_ta/core.py` -> `AnalysisIndicators.g191_109` (accessor),
`tests/test_g191_109.py` (tests). `README.md`'s headline (`310 -> 311` / `318 -> 319`) and
`volatility (31 -> 32)` row, and `docs/IndicatorDictionary.md` (regenerated, `311` probed), both
updated and checked by `tests/test_readme_counts.py`.
`docs/MLCompanionContract.md`'s running tag count updated **655 -> 656 / 298 -> 299 `SF`**
(`G191_109_10_2_10_2` probes cleanly at the dictionary's 600-bar synthetic frame and takes many
distinct values, so the generator tags it `SF`), checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match (`310 -> 311`) and
`CATEGORY_BUCKETS["volatility"]` updated (`31 -> 32`).

`g191_109`'s Gate E row is NOT yet in `docs/gate_e_ledger.csv`, per this session's override
rules (issue-solver runs Gate E after this session; a later receipt session records the ledger
row and fills in the measured numbers above). This is expected to leave
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` failing on this
tree until that happens (see Suite run below).

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order: **3 failed, 5122 passed, 83
skipped**. `g191_109`'s own tests (`tests/test_g191_109.py`): **17 passed**. The 3 failures,
all pre-existing or expected-until-the-launcher's-run (CLAUDE.md "Known breaks" plus this
port's own owed Gate E ledger row, see above):
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (reports
`['g191_109', 'mtd_ret']` missing -- `g191_109`'s row above; `mtd_ret` is a pre-existing,
unrelated indicator, issue #206, out of this issue's scope), `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this worktree) and
`tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` (untracked
`docs/pine/` corpus). No other test regresses.
