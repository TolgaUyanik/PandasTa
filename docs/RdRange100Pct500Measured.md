# Percentile of the 100-Bar Range Among the Last 500 — measured (`rd_range100_pct500`)

PandasTa issue #169. Source: Reddit, tier 4 (ResearchIntel kb/reddit.db): r/algotrading
`rd:algotrading:1nrkjby` (2025-09-27), https://www.reddit.com/r/algotrading/comments/1nrkjby/ —
"measured the percent change between highest high and lowest low for about 100 periods. Then
measure that variable's lowest 20th percentile value over 500 periods." Claimed use (tier 4,
untested by the poster): flags choppy/consolidating markets.

**Status: Gates A–D cleared this session. Gate E: pending, run by issue-solver after this
session.** `rd_range100_pct500` is wired into `Category["volatility"]`; `tests/test_gate_e_ledger.py
::test_every_indicator_that_needs_a_row_has_one` fails until the ledger row is recorded — expected,
not a defect (see CLAUDE.md "Owed, not failed, on the way to `dev`").

Shipped: `pandas_ta/volatility/rd_range100_pct500.py`, one column
`RD_RANGE100_PCT500_{length}_{pctlen}` (default `RD_RANGE100_PCT500_100_500`). Tests:
`tests/test_rd_range100_pct500.py` (15). Numbers: `python docs/measure_rd_range100_pct500.py` and
`python docs/measure_rd_range100_pct500_cpu.py`. Environment: Python 3.11.2, pandas 2.3.3, numpy
1.26.4. Measured 2026-11-25.

## The shipped form is the issue's own stated scale-free form, not the poster's boolean

The poster's rule is a threshold test: "chop if R <= its 20th percentile." The issue text names the
shipped candidate itself as the scale-free form that was actually screened and measured: "Prototype:
`docs/issues/screen/ind_screen_r6.py`, candidate `rd_range100_pct500` (scale-free form: percentile
rank of R over 500 bars)." This port ships that percentile rank directly — a continuous value on
`[0, 1]` — not the poster's own boolean cutoff. The caller can threshold it at 0.20 to recover the
poster's exact rule; shipping the rank itself is strictly more information and matches what Gate E
was run against (0.4037 vs `natr_Pctl`, quoted in the issue, not re-measured in this session).

## Gate A — the formula, read bar-by-bar

    R                     = (HHV(high, 100) - LLV(low, 100)) / LLV(low, 100)
    RD_RANGE100_PCT500    = percentile rank of R over the trailing 500 bars

`HHV`/`LLV` are Pine's trailing-window highest-high / lowest-low, INCLUSIVE of the current bar —
`Series.rolling(100).max()` / `.min()` read the identical window. The percentile rank uses pandas'
own `Series.rolling(500).rank(pct=True, method="max")`, matching the prototype's own choice of
`method="max"` (a bar whose `R` TIES another bar's within the 500-bar window reads the HIGHER of the
two ranks, not an average).

Division by `LLV(low, 100)`: the prototype's own `sdiv` helper (`docs/issues/screen/ind_screen.py`)
turns a `+-inf` result (only reachable if a window's lowest low is exactly `0.0`) into NaN; this
module matches that by calling `.replace([np.inf, -np.inf], np.nan)` on `R` before ranking — there is
no zero-guard in the poster's words or the prototype to diverge from, so this is the natural read of
"the prototype's own form," not an invented addition.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass | An independent per-window Python loop (plain `max()`/`min()` over NumPy slices, a manual `(window <= cur).sum() / pctlen` rank count — never calling the module's own rolling helpers) matches the shipped column on 102 of 102 compared bars of a 700-bar synthetic OHLC walk, max\|diff\| 0.0 (exact). A hand-derived constant-range frame (`high` fixed at 110, `low` fixed at 100 for 650 bars, so every `R` reading is identical) reads exactly `1.0` on all 52 fired bars, pinning the `method="max"` tie rule. |
| B Causality | pass | 8-offset future-perturbation sweep (curated to skip the one position whose own rank already sat at the 500-bar ceiling before perturbing, since a ceiling-pinned rank cannot visibly rise further — see `tests/test_rd_range100_pct500.py`'s `_leaks` docstring): real module leaks at 0 of 8. A mutant (`importlib`-read source, the percentile-rank input shifted toward the future with `.shift(-1)` before ranking, `exec`'d in memory) is live (differs from the real module) and caught at 8 of 8 offsets. |
| C Reachability | pass | Synthetic: 1,200-bar OHLC walk (seed 11/21, σ=0.02): 602 of 1,200 finite (598-bar warm-up: a 100-bar range window feeding a 500-bar rank window), 126 distinct values, range [0.002000, 1.000000]. Ten independent 1,200-bar seeds: 602 non-NaN of 1,200 on every seed, 175–297 distinct values. Real-data reachability: owed with Gate E. |
| D Scale-free | pass | ×8 / ×64 bit-identical on all 602 fired bars with matching NaN masks (both `HHV` and `LLV` are linear in a joint positive rescale of `high` and `low`, and `k*a / k*b == a / b` exactly under a power-of-two `k` in IEEE float; a percentile RANK of an unchanged series is itself unchanged, so no further error enters at the ranking step). ×10 / ×3.7 within 0.0 absolute (exact: rank is a count over an unchanged relative ordering, not a continuous arithmetic result, so even a non-power-of-two rescale that leaves every pairwise `R` comparison's sign unchanged reproduces the identical rank). `0 < 602 < 1,200` fires, 126 distinct values (non-constant). A synthetic zero low (`low[200] = 0.0`) divides to NaN, not `+-inf` (0 infinities in the output). Re-run clean with `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` (`docs/measure_rd_range100_pct500_cpu.py`): same 15/15 tests pass — no exact bit-count or Spearman digit beyond a stated tolerance is pinned, so the CPU-variant kernels on a GitHub runner cannot break this suite. |
| E Attribution | **pending** | Gate E: pending, run by issue-solver after this session. The issue's own prototype measurement (2026-10-25, quoted, NOT re-run here): max \|ρ\| 0.4037 vs `natr_Pctl` (manifest, n = 345,627; per-frame max median 0.3964) → SHIP under the issue's own ship line. |
| F Suites | this repo only (per the porting rules, the launcher runs both whole suites) | `python -m pytest -q tests/test_rd_range100_pct500.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`: see "Final suite run" below. Whole suites: run by issue-solver in clean worktrees (see the PR body). |

## Why a single-bar future perturbation cannot push `R` both ways

`HHV`/`LLV` are rolling MAX/MIN over 100 bars. Modifying only the ONE bar a causality probe is
allowed to touch at offset `j` (bars `< j` must stay untouched, by the test's own definition) can
reliably push `R[j]` UP — scale `high[j]` by 1000 and it is virtually certain to become the window's
new maximum regardless of the other 99 bars — but cannot reliably push `R[j]` DOWN: shrinking a
single interior bar's `high` toward its own `low` only changes `HHV` if that bar already happened to
be the window's existing argmax, which is a 1-in-100 event, not something a single edit can force.
This is why `tests/test_rd_range100_pct500.py`'s causality probe uses one deterministic UP-spike
(not a symmetric pair) and curates `OFFSETS` to avoid the one case that tool cannot show: a bar whose
rank was already pinned at `1.0` before the spike. Both are documented in the test module and this
file rather than left as something a future reader has to re-derive.

## The dictionary's 600-bar probe cannot classify this column — measured `SF` separately

`docs/gen_indicator_dictionary.py` probes every indicator against a 600-bar synthetic frame. This
column's own warm-up is 598 bars (measured above), leaving at most 2 non-NaN bars in that probe —
`classify()` needs ≥ 20 co-finite bars between the unscaled and 137×-scaled frames to call a scale,
and falls back to `unknown` (`??`) below that. `docs/MLCompanionContract.md`'s running tally records
this column under `??`, not `SF`, to match the dictionary table exactly (the same convention as
`stl_spikiness`'s `CONST` entry), with this file and that paragraph stating the actually-measured
classification: `SF`, bit-identical under ×8/×64 and exact under ×10/×3.7 (Gate D, above), on a
1,200-bar frame that gives the column room to fire 602 times.

## Wiring counts, read back

`Category` total 411 (dev stood at 410 by the time this branch rebased onto it, carrying
PRs #395/#397/#399/#401/#379/#378 and #402's `b3_outside_pivot3`; this port's own +1 makes 411),
`Category["volatility"]` 42 (was 41; `b3_outside_pivot3` and dev's other interleaving merges
landed in other categories, so they did not move this bucket). README headline and the
`volatility (42)` row updated to match; `docs/IndicatorDictionary.md` regenerated (413 indicator
rows across 9 categories, this column's own row still `??`-tagged, warm-up 598);
`docs/MLCompanionContract.md`'s running `??` tally updated 21 → 22 (756 tagged columns total, was
755 after the merged PRs' own bumps); `CATEGORY_TOTAL` 411 and `CATEGORY_BUCKETS["volatility"]` 42
in `tests/test_altport2_ports.py`. All of the above re-measured 2026-11-26 after rebasing onto
`dev`, re-running `tests/test_readme_counts.py` (6 passed).

## Final suite run

`python -m pytest -q tests/test_rd_range100_pct500.py tests/test_readme_counts.py
tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
— 1,577 passed, 7 skipped, 1 failed (`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
— expected, Gate E owed), measured 2026-11-25. Both repos' whole suites: run by issue-solver in clean
worktrees (see the PR body).

## Next step

Gate E run owed: `../Backtesting/Backtesting/scripts/analysis/gate_e_overlap.py run --module
pandas_ta.volatility.rd_range100_pct500 --name rd_range100_pct500`, then
`python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD`. A later receipt session
records the ledger row and the measured Gate E numbers in this file.
