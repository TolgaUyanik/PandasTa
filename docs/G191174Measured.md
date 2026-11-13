# g191_174 — measured (issue #74)

> **Status: Gates A-F cleared. Gate E measured 2026-11-10: DISCLOSE, max|rho| 0.7885 vs
> `mad_pct` -- under the 0.90 strike line, column ships. Ledger row recorded.
> This repo's suite green except the pre-existing breaks below.**

Up-day volatility EMA: Guotai Junan's (2017, "GTJA191", internal quant report, read via the
HKUDS/Vibe-Trading copy, MIT) alpha `#174`, per issue #74's own instruction. Module
`pandas_ta/volatility/g191_174.py`, column `G191_174_20_20_1`. Tests: `tests/test_g191_174.py`
(17, all passing). Numbers below: `python docs/measure_g191_174.py`. Environment: this
worktree's pinned pandas/numpy, per `docs/IndicatorDictionary.md`'s header. Measured
2026-11-10.

## Gate A: derivation from the published formula, not the prototype

Issue #74 states GTJA191 alpha `#174`:

    SMA(C>C1 ? STD(C,20) : 0, 20, 1)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web access are both
unavailable in this worktree, so the issue's own named copy -- HKUDS/Vibe-Trading (MIT) -- was
never read. Everything below is derived from the issue's own stated formula string, per the
issue's own rule ("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype (`docs/issues/screen/ind_screen.py:544-547`):

    @cand("g191_174", "up-day volatility EMA", G,
          "#174: SMA(C>C1 ? STD(C,20) : 0, 20, 1)", "/close")
    def _(o, h, l, c, v):
        s = std(c, 20)
        return sma(s.where(c > delay(c, 1), 0.0).where(s.notna()), 20, 1) / c

No disclosed interpretation choice was needed -- the issue's own string and the prototype
agree exactly, including the window lengths. Unlike `g191_023` (issue #73), this alpha is NOT
a ratio of two same-unit accumulators: it is the single up-day accumulator alone, which carries
the unit of `STD(C,20)` -- a price-scale quantity. The prototype's own `conv` field records
this directly (`docs/issues/screen/candidates.csv`'s `g191_174` row: `/close`), and this port
applies that division, matching the issue's own candidate line, "(scale-free form: /close)".

Operators, each read directly off the prototype's own module source: `DELAY(X,n) = X.shift(n)`
(`ind_screen.py:45`), `STD(X,n) = X.rolling(n).std()` (`ind_screen.py:48`, pandas default
`ddof=1`, the same convention `g191_076` (issue #54), `g191_160` (issue #67) and `g191_023`
(issue #73) established for the identical GTJA `STD` operator), and `SMA(A,n,m)` -- NOT this
fork's plain simple-moving-average `sma` but GTJA's own recursive smoother, called out
explicitly in the prototype's own docstring (`ind_screen.py:57-59`): `Y[t] = (m*A[t] +
(n-m)*Y[t-1])/n`, an EMA with `alpha = m/n`. The same operator and the same
`ewm(alpha=m/n, adjust=False, min_periods=n)` implementation already ships in `g191_160` and
`g191_023` for the identical GTJA `SMA`.

### The structure: a single accumulator, scaled

The ternary (`C>C1 ? STD(C,20) : 0`) routes every bar's trailing rolling std to a single
up-day accumulator (zero on down-or-flat days), smoothed by GTJA's own recursion, then divided
by close. Unlike `g191_023`/`g191_160`'s complementary-pair ratio (where the price unit cancels
between numerator and denominator), this column keeps the raw price-scale unit from `STD(C,20)`
until the final `/close` division makes it scale-free. This naming (`std_c`, `up_vol`, `u`) is
used throughout the module and this document.

### Warm-up: a disclosed necessary condition

`std_c = STD(C,20)` needs 20 CONSECUTIVE bars of `C`, so it is undefined for the first 19 bars.
`up_vol` inherits that exact same mask (the prototype's own trailing `.where(s.notna())`, read
literally in the module as `.where(std_c.notna())`). The final GTJA `SMA`, `min_periods=20`,
needs 20 more CONSECUTIVE valid `up_vol` values. Total: `min_length = std_length +
smooth_length - 1` = `20+20-1` = **39** bars at the shipped defaults, enforced by
`verify_series`.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula, matching the issue's own prototype line-for-line | An 8-bar hand-derived example (`std_length=3, smooth_length=3, smooth_weight=1`) checked against an independent computation of `STD`/the ternary/GTJA `SMA`/`/close` (`python docs/measure_g191_174.py`), matching the module's float64 output exactly at bars 4-7, plus an independent per-bar loop (plain numpy `np.std(ddof=1)`, not the module's own `.rolling()`/`.ewm()` calls) spot-checked at the shipped defaults on a 900-bar frame at bars 300/600/899 (differences 2.5e-15 to 6.6e-15, within float round-off) |
| B Causality | pass | Future-perturbation sweep (close series rewritten from `j` onward), 34 offsets past the 38-bar warm-up: real module **0 of 34** leaks. Write-shift mutant (final write index `smooth_length=20` bars into the future): caught **34 of 34**. Centered-std mutant (`std_c = close.rolling(std_length, center=True).std()`, the `bos` look-ahead bug class): caught **34 of 34** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic close series (seed 11, lognormal walk, `docs/measure_g191_174.py:_walk`), shipped default: **1,462 of 1,500** bars non-NaN (97.47%), first valid at bar 38 (exactly the structural warm-up boundary, `min_length - 1`). **1,462 distinct values**. Range `[0.006771, 0.025463]`, median `0.012430`, no negative values observed |
| D Scale-free | pass | The up-day branch choice (`C>C1`) is invariant under a positive price rescale, and `STD`/GTJA `SMA` are both linear in a positive scalar multiple of their input, so `u` scales by the same factor as `close`; the final `/close` division is what cancels that factor exactly. Measured on the 1,500-bar series: PRICE x8/x64 **bit-identical, 0.0 max\|diff\|** (power-of-two multiplication is exact in IEEE754); x10/x3.7 **within float64 rounding tolerance** (max\|diff\| 3.06e-14 / 1.05e-14). `0 < 1462 fires < 1500` and `1462 > 1` distinct values rule out a constant column; no negative value observed on the fired bars |
| E Attribution | **DISCLOSE** (0.76 <= \|rho\| < 0.80, under the 0.90 strike line) | Spearman, 89 ALTPORT-1 frames, 398,849 pooled bars, 687 comparators (329 `compute_all` + 358 manifest), canary `AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS` bit-equal. `G191_174_20_20_1`: max\|rho\| **0.7885** vs `mad_pct` (manifest, n=395,467); per-frame max median **0.7747** (also `mad_pct`, 89 frames, 0% of frames >= 0.90). Run `is74-g191_174-716f26eb`, recorded in `docs/gate_e_ledger.csv` |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **308 -> 309** (`volatility` **30 -> 31**); `df.ta.<name>()` accessor count **316 ->
317**. Touch points: `pandas_ta/volatility/g191_174.py` (module),
`pandas_ta/volatility/__init__.py` (export), `pandas_ta/__init__.py` -> `Category["volatility"]`
(discovery), `pandas_ta/core.py` -> `AnalysisIndicators.g191_174` (accessor),
`tests/test_g191_174.py` (tests). `README.md`'s headline (`308 -> 309` / `316 -> 317`) and
`volatility (30 -> 31)` row, and `docs/IndicatorDictionary.md` (regenerated, `310 -> 311`
probed), both updated and checked by `tests/test_readme_counts.py`.
`docs/MLCompanionContract.md`'s running tag count updated **653 -> 654 / 296 -> 297 `SF`**
(`G191_174_20_20_1` probes cleanly at the dictionary's 600-bar synthetic frame and takes many
distinct values, so the generator tags it `SF`), checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match (`308 -> 309`) and
`CATEGORY_BUCKETS["volatility"]` updated (`30 -> 31`).

`g191_174`'s Gate E row is recorded in `docs/gate_e_ledger.csv` (verdict `DISCLOSE`, run
`is74-g191_174-716f26eb`, measured 2026-11-10).

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order (receipt session, after the Gate E
ledger row above was recorded): **3 failed, 5078 passed, 83 skipped**. `g191_174`'s own tests
(`tests/test_g191_174.py`): **17 passed**. The 3 failures, none caused by this port:

- `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` -- NOT
  `g191_174` (its row is recorded, confirmed by a one-off probe of `gl.read_ledger()` /
  `gl.read_grandfathered()` against `ta.Category`: `MISSING: ['mtd_ret']`). `mtd_ret` is a
  pre-existing, unrelated indicator (`14a7515`/`6db7948`, issue #206) with its own owed Gate E
  row; out of this issue's scope.
- `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows` (needs the
  sibling `../AlternativeRepos` checkout, absent in this worktree) -- pre-existing, per
  CLAUDE.md.
- `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` (untracked
  `docs/pine/` corpus) -- pre-existing, per CLAUDE.md "Known breaks".

No other test regresses.
