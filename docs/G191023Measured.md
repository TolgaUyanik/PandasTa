# g191_023 — measured (issue #73)

> **Status: Gates A-E cleared, DISCLOSE. This repo's suite green except the pre-existing
> breaks below.**

Up-day volatility share (Dorsey RVI form): Guotai Junan's (2017, "GTJA191", internal quant
report, read via the HKUDS/Vibe-Trading copy, MIT) alpha `#23`, per issue #73's own
instruction. Module `pandas_ta/volatility/g191_023.py`, column `G191_023_20_20_1`. Tests:
`tests/test_g191_023.py` (17, all passing). Numbers below: `python docs/measure_g191_023.py`.
Environment: this worktree's pinned pandas/numpy, per `docs/IndicatorDictionary.md`'s header.
Measured 2026-11-10.

## Gate A: derivation from the published formula, not the prototype

Issue #73 states GTJA191 alpha `#23`:

    SMA(C>C1 ? STD(C,20) : 0, 20, 1) / (that + SMA(C<=C1 ? STD(C,20) : 0, 20, 1)) * 100

**What this session could NOT do, disclosed up front:** `docs/pine/` and web access are both
unavailable in this worktree, so the issue's own named copy -- HKUDS/Vibe-Trading (MIT) -- was
never read. Everything below is derived from the issue's own stated formula string, per the
issue's own rule ("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype (`docs/issues/screen/ind_screen.py:324-330`):

    @cand("g191_023", "up-day volatility share (Dorsey RVI form)", G,
          "#23: SMA(C>C1 ? STD(C,20) : 0, 20, 1) / (that + SMA(C<=C1 ? STD(C,20) : 0, 20, 1)) * 100")
    def _(o, h, l, c, v):
        s, up = std(c, 20), c > delay(c, 1)
        u = sma(s.where(up, 0.0).where(s.notna()), 20, 1)
        d = sma(s.where(~up, 0.0).where(s.notna()), 20, 1)
        return 100 * sdiv(u, u + d)

No disclosed interpretation choice was needed -- the issue's own string and the prototype
agree exactly, including both window lengths. Unlike `g191_160` (the down-day counterpart,
issue #67), this alpha carries NO `conv` field in the prototype registry
(`docs/issues/screen/candidates.csv`'s `g191_023` row leaves the conversion column blank): a
ratio of two same-unit (price-std) quantities is already scale-free by construction, so no
`/close` division is applied, matching the issue's own candidate line.

Operators, each read directly off the prototype's own module source: `DELAY(X,n) = X.shift(n)`
(`ind_screen.py:45`), `STD(X,n) = X.rolling(n).std()` (`ind_screen.py:48`, pandas default
`ddof=1`, the same convention `g191_076` (issue #54) and `g191_160` (issue #67) established for
the identical GTJA `STD` operator), and `SMA(A,n,m)` -- NOT this fork's plain simple-moving-
average `sma` but GTJA's own recursive smoother, called out explicitly in the prototype's own
docstring (`ind_screen.py:57-59`): `Y[t] = (m*A[t] + (n-m)*Y[t-1])/n`, an EMA with `alpha =
m/n`. The same operator and the same `ewm(alpha=m/n, adjust=False, min_periods=n)`
implementation already ships in `g191_160` for the identical GTJA `SMA`.

### The structure: a complementary pair, ratioed

The two ternaries (`C>C1 ? STD(C,20) : 0` and `C<=C1 ? STD(C,20) : 0`) partition every bar into
exactly one of two accumulators -- an up-day accumulator and a down-or-flat-day accumulator --
each smoothed independently by GTJA's own recursion; the result is the up-accumulator's share
of the two accumulators' sum, times 100 (the Dorsey Relative Volatility Index's 0-100
convention). This naming (`std_c`, `up_vol`, `dn_vol`, `u`, `d`) is used throughout the module
and this document.

### Warm-up: a disclosed necessary condition

`std_c = STD(C,20)` needs 20 CONSECUTIVE bars of `C`, so it is undefined for the first 19 bars.
`up_vol`/`dn_vol` each inherit that exact same mask (the prototype's own trailing
`.where(s.notna())`, read literally in the module as `.where(std_c.notna())`). The final GTJA
`SMA`s, `min_periods=20` each, need 20 more CONSECUTIVE valid `up_vol`/`dn_vol` values. Total:
`min_length = std_length + smooth_length - 1` = `20+20-1` = **39** bars at the shipped
defaults, enforced by `verify_series`.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula, matching the issue's own prototype line-for-line | An 8-bar hand-derived example (`std_length=3, smooth_length=3, smooth_weight=1`) checked against an independent computation of `STD`/the ternary pair/GTJA `SMA` (`python docs/measure_g191_023.py`), matching the module's float64 output exactly at bars 4-7, plus an independent per-bar loop (plain numpy `np.std(ddof=1)`, not the module's own `.rolling()`/`.ewm()` calls) spot-checked at the shipped defaults on a 900-bar frame at bars 300/600/899 (differences 3.8e-13 to 5.0e-13, within float round-off) |
| B Causality | pass | Future-perturbation sweep (close series rewritten from `j` onward), 34 offsets past the 38-bar warm-up: real module **0 of 34** leaks. Write-shift mutant (final ratio write index `smooth_length=20` bars into the future): caught **34 of 34**. Centered-std mutant (`std_c = close.rolling(std_length, center=True).std()`, the `bos` look-ahead bug class): caught **34 of 34** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic close series (seed 11, lognormal walk, `docs/measure_g191_023.py:_walk`), shipped default: **1,462 of 1,500** bars non-NaN (97.47%), first valid at bar 38 (exactly the structural warm-up boundary, `min_length - 1`). **1,462 distinct values**. Range `[22.643164, 83.292691]`, median `50.381575` -- within the structural `[0, 100]` bound |
| D Scale-free | pass | The up/down-day branch choice (`C>C1`) is invariant under a positive price rescale, and `STD`/GTJA `SMA` are both linear in a positive scalar multiple of their input, so `u` and `d` both scale by the same factor as `C`, cancelling exactly in the ratio -- no final division by `C` is even needed. Measured on the 1,500-bar series: PRICE x8/x64 **bit-identical, 0.0 max\|diff\|** (power-of-two multiplication is exact in IEEE754); x10/x3.7 **within float64 rounding tolerance** (max\|diff\| 1.80e-11 / 6.45e-12). `0 < 1462 fires < 1500` and `1462 > 1` distinct values rule out a constant column; the column also stays within its structural `[0, 100]` bound on every fired bar |
| E Attribution | **DISCLOSE** (0.76 <= rho < 0.80) -- column stays, no strike | `gate_e_overlap.py run --module pandas_ta.volatility.g191_023`, 89 ALTPORT-1 frames, 398,849 pooled bars (395,467 non-NaN/non-zero), 687 comparators (329 `compute_all` + 358 manifest). `G191_023_20_20_1`: max\|rho\| **0.7904** vs `psl` (`compute_all`, n=395,467); per-frame max median \|rho\| **0.7848** (89 frames, 0.0% of frames >= 0.90); manifest-only max\|rho\| 0.7664 vs `Pct_Up_Days_63`. Canary (AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS) bit-equal. Run recorded in `docs/gate_e_ledger.csv`, measured 2026-11-10 |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **307 -> 308** (`volatility` **29 -> 30**); `df.ta.<name>()` accessor count **315 ->
316**. Touch points: `pandas_ta/volatility/g191_023.py` (module),
`pandas_ta/volatility/__init__.py` (export), `pandas_ta/__init__.py` -> `Category["volatility"]`
(discovery), `pandas_ta/core.py` -> `AnalysisIndicators.g191_023` (accessor),
`tests/test_g191_023.py` (tests). `README.md`'s headline (`307 -> 308` / `315 -> 316`) and
`volatility (29 -> 30)` row, and `docs/IndicatorDictionary.md` (regenerated, `309 -> 310`
probed), both updated and checked by `tests/test_readme_counts.py`.
`docs/MLCompanionContract.md`'s running tag count updated **652 -> 653 / 295 -> 296 `SF`**
(`G191_023_20_20_1` probes cleanly at the dictionary's 600-bar synthetic frame and takes many
distinct values, so the generator tags it `SF`), checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match (`307 -> 308`) and
`CATEGORY_BUCKETS["volatility"]` updated (`29 -> 30`).

`g191_023`'s Gate E row is recorded in `docs/gate_e_ledger.csv` (DISCLOSE, measured
2026-11-10, run `is73-g191_023-7cb8fc00`).

## Suite run (this repo, this receipt session)

`python -m pytest -q`, full suite, default collection order: **3 failed, 5053 passed, 83
skipped**. `g191_023`'s own tests (`tests/test_g191_023.py`): **17 passed**. The 3 failures
are all pre-existing and unrelated to this port (CLAUDE.md "Known breaks"):
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (owed row for
`mtd_ret`, issue #206, not `g191_023` -- `g191_023`'s own row is recorded above),
`tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this worktree) and
`tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` (untracked
`docs/pine/` corpus). No other test regresses.
