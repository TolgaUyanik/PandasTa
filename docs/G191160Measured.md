# g191_160 — measured (issue #67)

> **Status: Gates A-E cleared, SHIP. This repo's suite green except the pre-existing breaks
> below.**

Down-day volatility EMA: Guotai Junan's (2017, "GTJA191", internal quant report, read via
the HKUDS/Vibe-Trading copy, MIT) alpha `#160`, per issue #67's own instruction. Module
`pandas_ta/volatility/g191_160.py`, column `G191_160_20_20_1`. Tests:
`tests/test_g191_160.py` (16, all passing). Numbers below: `python docs/measure_g191_160.py`.
Environment: this worktree's pinned pandas/numpy, per `docs/IndicatorDictionary.md`'s header.
Measured 2026-11-10.

## Gate A: derivation from the published formula, not the prototype

Issue #67 states GTJA191 alpha `#160`:

    SMA(C<=C1 ? STD(C,20) : 0, 20, 1)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web access are both
unavailable in this worktree, so the issue's own named copy -- HKUDS/Vibe-Trading (MIT) -- was
never read. Everything below is derived from the issue's own stated formula string, per the
issue's own rule ("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype (`docs/issues/screen/ind_screen.py:521-524`):

    @cand("g191_160", "down-day volatility EMA", G,
          "#160: SMA(C<=C1 ? STD(C,20) : 0, 20, 1)", "/close")
    def _(o, h, l, c, v):
        s = std(c, 20)
        return sma(s.where(c <= delay(c, 1), 0.0).where(s.notna()), 20, 1) / c

No disclosed interpretation choice was needed -- the issue's own string and the prototype
agree exactly, including both window lengths and the `/close` scale-free conversion the
issue's own candidate line states. Operators, each read directly off the prototype's own
module source: `DELAY(X,n) = X.shift(n)` (`ind_screen.py:45`), `STD(X,n) = X.rolling(n).std()`
(`ind_screen.py:48`, pandas default `ddof=1`, the same convention `g191_076` (issue #54)
established for the identical GTJA `STD` operator), and `SMA(A,n,m)` -- NOT this fork's plain
simple-moving-average `sma` but GTJA's own recursive smoother, called out explicitly in the
prototype's own docstring (`ind_screen.py:55-58`): `Y[t] = (m*A[t] + (n-m)*Y[t-1])/n`, an EMA
with `alpha = m/n`. The same operator and the same `ewm(alpha=m/n, adjust=False,
min_periods=n)` implementation already ships in `g191_152` and `g191_146` for the identical
GTJA `SMA`.

### The structure: a conditional volatility, smoothed

The ternary (`C<=C1 ? STD(C,20) : 0`) picks ONLY the down-or-flat-day bars' contribution to a
rolling std of close, forcing every up-day bar to zero; the GTJA recursion then smooths that
per-bar series, and the issue's own candidate line divides the whole thing by close for a
scale-free result. This naming (`std_c`, `down_vol`) is used throughout the module and this
document.

### Warm-up: a disclosed necessary condition

`std_c = STD(C,20)` needs 20 CONSECUTIVE bars of `C`, so it is undefined for the first 19
bars. `down_vol` inherits that exact same mask (the prototype's own trailing
`.where(s.notna())`, read literally in the module as `.where(std_c.notna())`). The final GTJA
`SMA`, `min_periods=20`, needs 20 more CONSECUTIVE valid `down_vol` values. Total:
`min_length = std_length + smooth_length - 1` = `20+20-1` = **39** bars at the shipped
defaults, enforced by `verify_series`.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula, matching the issue's own prototype line-for-line | An 8-bar hand-derived example (`std_length=3, smooth_length=3, smooth_weight=1`) checked against an independent computation of `STD`/the ternary/GTJA `SMA` (`python docs/measure_g191_160.py`), matching the module's float64 output exactly at bars 4-7, plus an independent per-bar loop (plain numpy `np.std(ddof=1)`, not the module's own `.rolling()`/`.ewm()` calls) spot-checked at the shipped defaults on a 900-bar frame at bars 300/600/899 (differences 2e-9 to 5e-9, within float round-off) |
| B Causality | pass | Future-perturbation sweep (close series rewritten from `j` onward), 34 offsets past the 38-bar warm-up: real module **0 of 34** leaks. Write-shift mutant (final GTJA-`SMA`/division write index `smooth_length=20` bars into the future): caught **34 of 34**. Centered-std mutant (`std_c = close.rolling(std_length, center=True).std()`, the `bos` look-ahead bug class): caught **34 of 34** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic close series (seed 11, lognormal walk, `docs/measure_g191_160.py:_walk`), shipped default: **1,462 of 1,500** bars non-NaN (97.47%), first valid at bar 38 (exactly the structural warm-up boundary, `min_length - 1`). **1,462 distinct values**. Range `[0.004948, 0.034365]`, median `0.011990` |
| D Scale-free | pass | The down/up-day branch choice (`C<=C1`) is invariant under a positive price rescale, and `STD`/GTJA `SMA` are both linear in a positive scalar multiple of their input, so the whole column scales exactly by the same factor as `C`, cancelling against the final division by `C`. Measured on the 1,500-bar series: PRICE x8/x64 **bit-identical, 0.0 max\|diff\|** (power-of-two multiplication is exact in IEEE754); x10/x3.7 **within float64 rounding tolerance** (max\|diff\| 3.32e-14 / 1.35e-14). `0 < 1462 fires < 1500` and `1462 > 1` distinct values rule out a constant column |
| E Attribution | pass, SHIP | Run `is67-g191_160-4e62a22b` (`gate_e_overlap.py run --module pandas_ta.volatility.g191_160`), 89 ALTPORT-1 frames, 398,849 pooled bars, 329 + 358 = 687 comparators, canary bit-equal on AKBNK/BIENY/AGHOL/SASA. `G191_160_20_20_1`: max \|ρ\| **0.7074** vs `mad_pct` (n=395,467), per-frame max median \|ρ\| **0.6782** (against `mad_pct`, 89 frames, 0% >= 0.90) -- under the SHIP line (< 0.76). Recorded in `docs/gate_e_ledger.csv`, measured 2026-11-10 |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **301 -> 302** (`volatility` **28 -> 29**); `df.ta.<name>()` accessor count **309 ->
310**. Touch points: `pandas_ta/volatility/g191_160.py` (module),
`pandas_ta/volatility/__init__.py` (export), `pandas_ta/__init__.py` -> `Category["volatility"]`
(discovery), `pandas_ta/core.py` -> `AnalysisIndicators.g191_160` (accessor),
`tests/test_g191_160.py` (tests). `README.md`'s headline (`301 -> 302` / `309 -> 310`) and
`volatility (28 -> 29)` row, and `docs/IndicatorDictionary.md` (regenerated, `303 -> 304`
probed), both updated and checked by `tests/test_readme_counts.py`.
`docs/MLCompanionContract.md`'s running tag count updated **646 -> 647 / 289 -> 290 `SF`**
(`G191_160_20_20_1` probes cleanly at the dictionary's 600-bar synthetic frame and takes many
distinct values, so the generator tags it `SF`), checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match (`301 -> 302`) and
`CATEGORY_BUCKETS["volatility"]` updated (`28 -> 29`).

`g191_160`'s Gate E row is recorded in `docs/gate_e_ledger.csv` (SHIP, measured 2026-11-10, this
receipt session). `mtd_ret` predates this session (carried over from issue #206, per
`docs/G191152Measured.md`'s identical note), unrelated to this port.

⚠ **A pre-existing, unrelated defect found while cross-checking README counts in a
non-default test order, disclosed here rather than fixed (out of this issue's scope):**
`core.py`'s `_indicators_by_category` returns `Category[name]` directly, not a copy;
`strategy()`'s `[ta.remove(x) for x in excluded if x in ta]` then mutates the live `Category`
list IN PLACE whenever a category sweep runs (e.g. `df.ta.strategy("trend")` permanently
removes `long_run`/`short_run` from `Category["trend"]` for the rest of the process). Running
`tests/test_wiring_accessors.py` before `tests/test_readme_counts.py` in the SAME pytest
process reproduces this (`momentum` and `trend` counts shrink by one and two respectively).
The default `python -m pytest -q` collection order (alphabetical by file) runs
`test_readme_counts.py` before `test_wiring_accessors.py`, so this is invisible there and in
every full-suite run quoted in this repo's prior `*Measured.md` files -- measured here, not
merely asserted, by running `tests/test_readme_counts.py` alone (no mismatch beyond this
port's own `volatility` count) versus the same file after
`tests/test_wiring_accessors.py tests/test_altport2_ports.py` (momentum/trend both wrong).
Not touched by this session: `core.py` is on the allowed-modify list, but fixing a pre-existing
defect unrelated to issue #67 is out of this port's scope.

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order: **3 failed, 4891 passed, 83
skipped**. `g191_160`'s own tests (`tests/test_g191_160.py`): **16 passed**. The 3 failures,
all pre-existing and unrelated to this port (CLAUDE.md "Known breaks" plus the owed Gate E
ledger row, see above): `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
(owed list above), `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this worktree) and
`tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` (untracked
`docs/pine/` corpus). No other test regresses.
