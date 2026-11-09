# g191_098 — measured (issue #58)

> **Status: Gates A-E cleared, SHIP. Gate F: this repo's suite green**
> **modulo pre-existing/expected failures (below).**

100-day trend-gated drawdown / 3-day reversal: Guotai Junan's (2017,
"GTJA191", internal quant report, read via the HKUDS/Vibe-Trading copy,
MIT) alpha `#98`, per issue #58's own instruction. Module
`pandas_ta/trend/g191_098.py`, column `G191_098_100_3_0.05`. Tests:
`tests/test_g191_098.py` (17, all passing). Numbers below:
`python docs/measure_g191_098.py`. Environment: this worktree's pinned
pandas/numpy. Measured 2026-11-09.

## Gate A: derivation from the published formula, not the prototype

Issue #58 states GTJA191 alpha `#98`:

    DELTA(MEAN(C,100),100)/DELAY(C,100) <= 0.05 ? -(C-TSMIN(C,100)) : -DELTA(C,3)

with the issue's own annotation that the candidate ships in its scale-free
form, "/close".

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own named
copy -- HKUDS/Vibe-Trading (MIT) -- was never read. Everything below is
derived from the issue's own stated formula string plus its own
prototype's unambiguous operator definitions, per the issue's own rule
("Gate A starts from the source formula, not the prototype").

`DELAY(X,n) = X.shift(n)`, `DELTA(X,n) = X - X.shift(n)`,
`MEAN(X,n) = X.rolling(n).mean()`, `TSMIN(X,n) = X.rolling(n).min()` -- each
read directly off the issue's own named prototype's unambiguous module
docstring (`docs/issues/screen/ind_screen.py:45,46,47,51`), the same
operator family `g191_144` (issue #57) and `g191_165` (issue #55) relied
on. The formula is a ternary gated on how much the 100-bar average of
`close` has itself drifted over the last 100 bars, as a fraction of the
close 100 bars ago:

    gate = DELTA(MEAN(C,100),100) / DELAY(C,100)
    G191_098 = gate <= 0.05 ? -(C-TSMIN(C,100)) : -DELTA(C,3)

The issue's own prototype (`docs/issues/screen/ind_screen.py:445-449`)
spells out the identical ternary directly, already in its scale-free
("/close") form:

    g = delta(mean(c, 100), 100) / delay(c, 100)
    (pd.Series(np.where(g <= 0.05, -(c - tsmin(c, 100)), -delta(c, 3)),
               index=c.index) / c).where(g.notna())

No disclosed interpretation choice was needed for the formula itself -- the
issue's own string and the prototype agree exactly. One disclosed
hardening WAS made beyond the prototype's literal `np.where`: this port
replaces `+-inf` in `gate` with `NaN` before the `<= 0.05` comparison
(the prototype's `g` would instead let an inf-gate silently route to the
reversal branch via `inf <= 0.05 -> False`); the final `.where(gate.notna())`
mask already catches this case either way, so the hardening only makes the
masking explicit rather than changing any observed output (no inf was
observed on the measured frame).

### Warm-up: a disclosed necessary condition

`trend_mean[t] = MEAN(close,100)[t]` needs 100 bars, valid from `t >= 99`.
`gate[t] = DELTA(trend_mean,100)[t] / DELAY(close,100)[t]` needs BOTH
`trend_mean[t]` and `trend_mean[t-100]` valid, i.e. `t - 100 >= 99`, i.e.
`t >= 199` -- the binding constraint (looser than `DELAY(close,100)`,
`TSMIN(close,100)` and `DELTA(close,3)`, each needing far fewer bars at
the shipped defaults). So the whole column is NaN for strictly fewer than
200 bars of history; `min_length = max(2*length, reversal_length+1) = 200`
at defaults, enforced by `verify_series`. Measured: on the 1,500-bar
synthetic frame, first valid bar is exactly index 199 (the structural
boundary, no extension beyond it observed).

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula, matching the issue's own prototype line-for-line | 10-bar hand-derived example at `length=4, reversal_length=2, threshold=0.05` (`tests/test_g191_098.py::test_hand_derived_ten_bars_exercises_both_branches`), tracing `trend_mean`, `gate`, `drawdown` and `reversal` independently: `result[7..9] = [-0.3, 1.3157894736842106, 2.3333333333333335]`, bars 0-6 NaN (gate's own warm-up), matching the module's float64 output exactly (`python docs/measure_g191_098.py`). A second hand frame (`test_hand_derived_drawdown_branch`) exercises the OTHER branch (gate <= 0.05) and checks every valid bar against an independent per-bar loop. Matches an independent per-bar loop (plain numpy array slicing, not the module's own `.rolling()` calls) at the shipped default (`length=100, reversal_length=3`), 3 spot-checked bars (250, 500, 899) on a 900-bar synthetic frame, relative difference 0.0 at all three |
| B Causality | pass | Future-perturbation sweep (close series rewritten from `j` onward, another synthetic series), 32 offsets past the 199-bar warm-up: real module **0 of 32** leaks (`python docs/measure_g191_098.py`). Mutant 1 (`importlib` source read, `exec`'d in memory, shown live-different from the real module): shifting the final write index `length=100` bars into the future -- caught at **32 of 32**. Mutant 2: replacing the gate's backward `DELAY(close,100)` with a FORWARD shift (`close.shift(-100)`) -- caught at a **measured 21 of 32**, not every offset. Disclosed reason: the gate only feeds a `<= 0.05` step function, so a corrupted denominator leaks into the output only on the offsets where it actually flips which branch is selected; mutant 1 proves the harness catches every offset when the leak is continuous rather than step-gated, so the gap in mutant 2 is a property of this ternary formula, not a weaker test |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic close series (seed 11, see `docs/measure_g191_098.py:_close`), shipped default: **1,301 of 1,500** bars non-NaN (86.73%), first valid at bar 199 (exactly the structural warm-up boundary). Of those, **915 bars take the drawdown branch** (`gate <= 0.05`) and **386 bars take the reversal branch** (`gate > 0.05`) -- BOTH branches of the ternary fire on real-shaped data, not just one. **1,267 distinct values** observed (not a constant column), range `[-0.289941, 0.082892]`, median `-0.053172` |
| D Scale-free | pass | Under a positive price rescale, `trend_mean`, `DELTA(trend_mean,100)` and `DELAY(close,100)` all scale linearly by the same factor `k`, so `gate` is exactly invariant and the branch taken at every bar is identical pre- and post-rescale; `drawdown` and `reversal` both scale by `k` in whichever branch is active, and the final division by `close` (which also scaled by `k`) cancels it exactly. Measured on the 1,500-bar series: PRICE x8/x64 **bit-identical, 0.0 max\|diff\|** (power-of-two multiplication is exact in IEEE754, so the algebraic cancellation is also exact in float64). PRICE x10/x3.7: max\|diff\| **2.22e-16 / 1.94e-16** -- float64 rounding from the scalar multiply itself, far under the test's 1e-9 tolerance. `0 < 1,301 fires < 1,500` and `1,267 > 1` distinct values rule out a constant column |
| E Attribution | **SHIP** | Run by the launcher: `gate_e_overlap.py run --module pandas_ta.trend.g191_098`, 89 ALTPORT-1 frames, 398,849 pooled bars, 687 comparators (329 `compute_all` + 358 `ml_features` manifest). Column `G191_098_100_3_0.05`: pooled max \|ρ\| **0.5067** vs `cmo_Pctl` (manifest, n=381,138); per-frame max median \|ρ\| **0.5174** (also vs `cmo_Pctl`); `perframe_pct_frames_ge_090` = 0.0. Both bands (pooled and per-frame-median) land under the 0.76 SHIP line -- **SHIP**, no strike. Ledger row recorded: `docs/gate_e_ledger.csv` (`python docs/gate_e_ledger.py record <run dir> --measured 2026-11-09`), run dir `is58-g191_098-e820d44f` |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **292 -> 293** (`trend` **60 -> 61**); `df.ta.<name>()` accessor
count **300 -> 301**. Touch points: `pandas_ta/trend/g191_098.py` (module),
`pandas_ta/trend/__init__.py` (export), `pandas_ta/__init__.py` ->
`Category["trend"]` (discovery), `pandas_ta/core.py` ->
`AnalysisIndicators.g191_098` (accessor), `tests/test_g191_098.py` (tests).
`README.md`'s headline and `trend (61)` row, and
`docs/IndicatorDictionary.md` (regenerated), both updated and checked by
`tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s running tag
count updated **637 -> 638 / 280 -> 281 `SF`** (`G191_098_100_3_0.05`
probes cleanly at the dictionary's synthetic frame and takes many distinct
values, so the generator tags it `SF`); `tests/test_ml_companions.py`
re-derives these from the live dictionary and passes.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match
(292 -> 293) and `CATEGORY_BUCKETS["trend"]` (60 -> 61).

Gate E ledger row: recorded 2026-11-09, SHIP, max\|ρ\| 0.5067 vs `cmo_Pctl`
(`docs/gate_e_ledger.csv`).

## Suite run (this session)

`python -m pytest -q`, full suite, default collection order: **3 failed,
4664 passed, 83 skipped**. `g191_098`'s own tests (`tests/test_g191_098.py`):
**17 passed**. The 3 failures are pre-existing / expected, all unrelated to
this port's correctness (CLAUDE.md "Known breaks"):
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
(fails with `no Gate E ledger row for ['g191_098', 'mtd_ret']` -- `g191_098`
is this port's own owed row, by design per this session's rules;
`mtd_ret` pre-dates this session, per `docs/G191026Measured.md`'s identical
note), `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this worktree)
and `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
(untracked `docs/pine/` corpus, CLAUDE.md "Known breaks"). No other test
regresses.
