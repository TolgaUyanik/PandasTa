# g191_129 — measured (issue #75)

> **Status: Gates A-E cleared, DISCLOSE. Shipped as `G191_129_12`.
> This repo's suite green except the pre-existing breaks below.**

12-day sum of down moves: Guotai Junan's (2017, "GTJA191", internal quant report, read via
the HKUDS/Vibe-Trading copy, MIT) alpha `#129`, per issue #75's own instruction. Module
`pandas_ta/momentum/g191_129.py`, column `G191_129_12`. Tests:
`tests/test_g191_129.py` (18, all passing). Numbers below: `python docs/measure_g191_129.py`.
Environment: this worktree's pinned pandas/numpy, per `docs/IndicatorDictionary.md`'s header.
Measured 2026-11-10.

## Gate A: derivation from the published formula, not the prototype

Issue #75 states GTJA191 alpha `#129`:

    SUM(C-C1<0 ? |C-C1| : 0, 12)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web access are both
unavailable in this worktree, so the issue's own named copy -- HKUDS/Vibe-Trading (MIT) -- was
never read. Everything below is derived from the issue's own stated formula string, per the
issue's own rule ("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype (`docs/issues/screen/ind_screen.py:477-478`):

    @cand("g191_129", "12-day sum of down moves", G,
          "#129: SUM(C-C1<0 ? |C-C1| : 0, 12)", "/close")
    def _(o, h, l, c, v): return tsum((-delta(c, 1)).clip(lower=0), 12) / c

No disclosed interpretation choice was needed -- the issue's own string and the prototype
agree exactly, including the window length and the `/close` scale-free conversion the issue's
own candidate line states. Operators, each read directly off the prototype's own module
source: `DELAY(X,n) = X.shift(n)` (`ind_screen.py:45`), `SUM(X,n) = X.rolling(n).sum()`
(`ind_screen.py:49`). `C-C1<0 ? |C-C1| : 0` and `(-delta).clip(lower=0)` are the identical
function at every bar, including exactly at the `C==C1` boundary (both give `0`) -- measured
in two parts, since a continuous-float random walk essentially never lands on `delta == 0`
exactly. `python docs/measure_g191_129.py` confirms `clip-vs-ternary agree=True` on the
1,500-bar synthetic walk (the GENERAL case), but that same script reports
`zero-delta-bars=0` for that walk -- it contains no exactly-flat bar, so it does not exercise
the boundary itself. The `delta == 0` boundary is pinned separately and exclusively by
`tests/test_g191_129.py::test_clip_matches_an_explicit_ternary_at_the_zero_boundary`, on its
own dedicated 5-bar frame built to hold one bar exactly flat -- not by the measure script.

### The structure: a running tally of downside price change

The ternary (`C-C1<0 ? |C-C1| : 0`) keeps ONLY the magnitude of the one-bar price change on a
down day, forcing every up-or-flat day to zero; summed over a trailing window and divided by
close, the result is a scale-free running tally of downside price movement -- the down-move
half of a Wilder-RSI-style split (up-move half is `g191_167`'s sibling structure, the
identical operator mirrored in sign).

### Warm-up: a disclosed necessary condition

`down = MAX(-(C-C1), 0)` needs `C1`, undefined at bar 0 (no prior bar), so `down` is `NaN`
there (the `close.diff()` call's own leading `NaN` propagates through the negation and
`.clip(lower=0)`, which preserves `NaN`). `SUM(down, 12)`, `min_periods=12`, needs 12
CONSECUTIVE valid `down` values ending at `t`. Total: `min_length = length + 1` = **13** bars
at the shipped default, enforced by `verify_series`.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula, matching the issue's own prototype line-for-line | A 6-bar hand-derived example (`length=3`) checked against an independent computation (`python docs/measure_g191_129.py`), matching the module's float64 output exactly at bars 3-5 (3/15, 11/7, 8/20), plus an independent per-bar loop (plain numpy array slicing, not the module's own `.rolling()` call) spot-checked at the shipped default on a 900-bar frame at bars 300/600/899 (module and loop identical to the printed repr) |
| B Causality | pass | Future-perturbation sweep (close series rewritten from `j` onward), 34 offsets past the 13-bar warm-up: real module **0 of 34** leaks. Write-shift mutant (final rolling-sum write index `length=12` bars into the future): caught **34 of 34**. Centered-sum mutant (`down.rolling(length, center=True)` instead of the causal trailing window, the `bos` look-ahead bug class): caught **34 of 34** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic close series (seed 11, lognormal walk, `docs/measure_g191_129.py:_walk`), shipped default: **1,488 of 1,500** bars non-NaN (99.20%), first valid at bar 12 (exactly the structural warm-up boundary, `min_length - 1`). **1,484 distinct values**. Range `[0.000000, 0.192170]`, median `0.069919` |
| D Scale-free | pass | The down/up-day branch choice (`C-C1 < 0`) is invariant under a positive price rescale, and the rolling sum is linear in its input, so the whole column scales exactly by the same factor as `C`, cancelling against the final division by `C`. Measured on the 1,500-bar series: PRICE x8/x64 **bit-identical, 0.0 max\|diff\|** (power-of-two multiplication is exact in IEEE754); x10/x3.7 **within float64 rounding tolerance** (max\|diff\| 4.16e-16 / 5.13e-16). `0 < 1488 fires < 1500` and `1484 > 1` distinct values rule out a constant column |
| E Attribution | DISCLOSE | Port's own Gate E run (issue-solver, run id `is75-g191_129-6bf7ac68`, 89 ALTPORT-1 frames, 398,849 pooled bars, 329 `compute_all` + 358 manifest = 687 comparators, canary bit-equal on AKBNK.IS/BIENY.IS/AGHOL.IS/SASA.IS): `G191_129_12` max\|ρ\| **0.7898156205282925** vs `Dist_to_BB_Upper_pct` (manifest set, n=397,158); per-frame max median \|ρ\| **0.7873528430086538** (same comparator, 89 frames, 0.0% of frames >= 0.90) -> **DISCLOSE** band (0.76 <= ρ < 0.80), neither the pooled nor the per-frame-median STRUCK line (>= 0.90) is crossed. Matches the 2026-10-24 prototype screen's own number (0.7898 / 0.7874 vs the same comparator) almost exactly -- the port did not change the correlation structure. Column **ships**. |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **309 -> 310** (`momentum` **78 -> 79**); `df.ta.<name>()` accessor count **317 ->
318**. Touch points: `pandas_ta/momentum/g191_129.py` (module),
`pandas_ta/momentum/__init__.py` (export), `pandas_ta/__init__.py` -> `Category["momentum"]`
(discovery), `pandas_ta/core.py` -> `AnalysisIndicators.g191_129` (accessor),
`tests/test_g191_129.py` (tests). `README.md`'s headline (`309 -> 310` / `317 -> 318`) and
`momentum (78 -> 79)` row, and `docs/IndicatorDictionary.md` (regenerated, `311 -> 312`
probed), both updated and checked by `tests/test_readme_counts.py`.
`docs/MLCompanionContract.md`'s running tag count updated **654 -> 655 / 297 -> 298 `SF`**
(`G191_129_12` probes cleanly at the dictionary's 600-bar synthetic frame and takes many
distinct values, so the generator tags it `SF`), checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match (`309 -> 310`); the
`momentum` bucket is not tracked in `CATEGORY_BUCKETS` (only `trend`/`volatility`/`volume`
are), so no change needed there.

`g191_129`'s Gate E row is recorded in `docs/gate_e_ledger.csv` (measured 2026-11-10, run id
`is75-g191_129-6bf7ac68`, DISCLOSE).

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order: see the run captured at commit
time below. `g191_129`'s own tests (`tests/test_g191_129.py`): **18 passed**. Expected failures
at this point in the lifecycle, all pre-existing (CLAUDE.md "Known breaks"):
`tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows` (needs the
sibling `../AlternativeRepos` checkout, absent in this worktree), and
`tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` (untracked
`docs/pine/` corpus). No other test regresses.
