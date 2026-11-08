# a101_053 — measured (issue #48)

> **Status: Gates A-E cleared. SHIP.** Gate F (both repos' suites) is run by
> the launcher in clean worktrees; `python -m pytest -q` in this worktree is
> reported below for the record.

9-day change of the close-location ratio: Kakushadze's (2016, Wilmott, "101
Formulaic Alphas") Alpha101 `#53`, per issue #48's own instruction. Module
`pandas_ta/momentum/a101_053.py`, column `A101_053_9`. Tests:
`tests/test_a101_053.py` (14, all passing). Numbers below: `python
docs/measure_a101_053.py`. Environment: this worktree's pinned pandas/numpy.
Measured 2026-11-08.

## Gate A: derivation from the published formula, not the prototype

Issue #48 states Alpha101 `#53`:

    -delta(((close-low)-(high-close))/(close-low), 9)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- vnpy's `vnpy/alpha101` module (MIT) -- was never read. Everything below is
derived directly from the issue's own stated formula string, which needs no
ambiguous-operator resolution: `delta(x, d) = x - x.shift(d)` is the only
operator present, already established by `a101_021`/`a101_023`/`a101_043`.
Unlike those three, this formula carries no `mean`, `std`, `adv` or
`ts_rank` term, so no glossary ASSUMPTION is needed.

One modelling choice, not an ambiguity in the formula itself: the ratio's
denominator is `close - low`, which is exactly zero whenever a bar closes at
its own low -- a real, non-rare event (CLAUDE.md's `fvg` note measures
21.17% of BIST daily bars closing exactly at an extreme). The formula is
silent on this case; following this fork's own existing convention for a
ratio with a possible zero denominator (`a101_021`'s `volume/adv`,
`a101_043`'s `volume/adv`, both `.replace([np.inf, -np.inf], np.nan)`), the
signed infinity from the zero denominator is replaced with `NaN`.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | primary vnpy/Kakushadze text NOT consulted (no `docs/pine/`/web this session) -- self-consistent against the issue's own stated formula, no ambiguous operator to resolve | two hand-derived examples computed by hand from the formula text, not by re-running the module: an 8-bar example at `length=3` with no zero denominators (`tests/test_a101_053.py::test_hand_derived_eight_bars`, reproduced in `docs/measure_a101_053.py` as `hand-derived bars 0..7: [nan, nan, nan, -0.0, -0.0, -0.25, -0.0, -0.75]`), and a 5-bar example at `length=1` that deliberately drives `close == low` on two bars (`test_zero_denominator_is_nan_not_inf`, reproduced as `zero-denominator bars 0..4: [nan, nan, -0.16666666666666663, nan, nan]`) -- showing the zero-denominator ratio, and every delta that reads it, as `NaN`, never a signed infinity |
| B Causality | pass | Future-perturbation sweep (high, low and close all rewritten from `j` onward), 37 offsets past the 9-bar warm-up: real module **0 of 37** leaks (`python docs/measure_a101_053.py`). The shipped mutant shifts the whole write index 30 bars into the future (`result = (-d9).shift(-30)`, `importlib` source read, `exec`'d in memory): shown live (differs from the real module), then caught at **37 of 37** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic walk (seed 11, sigma=1.5%/bar on close, high/low built as `close * (1 +- abs(normal(0, sigma*0.5)))`), shipped default (`length=9`): **1,491 of 1,500** bars non-NaN (99.40%) -- exactly `n - 9`, the `length`-bar warm-up, no wider gap from the zero-denominator case on this particular walk. **1,491 distinct values** observed (not a constant column) |
| D Scale-free | pass | A joint high/low/close price rescale x8/x64: **bit-identical, 0.0 max\|diff\|** (`clr`'s numerator and denominator are both linear in `close, high, low`, so the ratio itself -- not merely a linearly-rescaled version of it -- is unchanged by a positive rescale; a difference of two unchanged quantities is unchanged too). x10/x3.7: max\|diff\| **1.19e-7** / **6.98e-8** -- NOT bit-identical and bigger than the 1e-9 other `a101_0*` ports' ratios hold to, because this ratio's own denominator (`close - low`) is a difference that comes arbitrarily close to zero (measured min \|close-low\| on this walk: 7.4e-5), so rescale-then-divide loses more bits there than a ratio with a clean price-level denominator (`a101_023`'s plain `close`). This is catastrophic cancellation, not a scale leak in the algebra -- the test's tolerance is loosened to 1e-6 to match what is actually measured, not invented. `0 < 1,491 fires < 1,500` and `1,491 > 1` distinct values rule out a constant column |
| E Attribution | **SHIP** | `A101_053_9` max \|ρ\| **0.6131** vs `CLV_Pctl` (manifest comparator set, n=311,906); per-frame max median \|ρ\| **0.6188** vs `CLV_Pctl`, 0.0% of 89 frames ≥ 0.90. Pooled compute_all-only max \|ρ\| 0.5221 vs `VOL_DELTA` (n=315,627). 687 comparators (329 compute_all + 358 manifest), 89 ALTPORT-1 frames, 398,849 pooled bars, canary bit-equal (AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS). Run `is48-a101_053-d596ef28`, recorded 2026-11-08 in `docs/gate_e_ledger.csv`. Well under the 0.76 SHIP line -- column kept. |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **280 → 281** (`momentum` **68 → 69**); `df.ta.<name>()` accessor
count **288 → 289**. Touch points: `pandas_ta/momentum/a101_053.py` (module),
`pandas_ta/momentum/__init__.py` (export), `pandas_ta/__init__.py` →
`Category["momentum"]` (discovery), `pandas_ta/core.py` →
`AnalysisIndicators.a101_053` (accessor), `tests/test_a101_053.py` (tests).
`README.md`'s headline and `momentum (69)` row, and `docs/IndicatorDictionary.md`
(regenerated), both updated and checked by `tests/test_readme_counts.py`.
`docs/MLCompanionContract.md`'s running tag count updated **625 → 626 / 268 →
269 `SF`** (`A101_053_9` probes cleanly at the dictionary's 600-bar synthetic
frame and is tagged `SF` there -- confirmed by reading the generated
`docs/IndicatorDictionary.md` row directly, not re-derived by hand);
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`
re-derives and passes against the updated `Counter`. `tests/test_altport2_ports.py`'s
`CATEGORY_TOTAL` updated to match (280 → 281); `CATEGORY_BUCKETS` is unaffected
(it tracks only `trend`/`volatility`/`volume`, not `momentum`).

`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
cleared once this session recorded the launcher's Gate E run (`is48-a101_053-d596ef28`)
into `docs/gate_e_ledger.csv`.

## Suite run (this repo, this session, after recording the Gate E row)

`python -m pytest -q`, full suite, default collection order: **2 failed,
4368 passed, 83 skipped**. `tests/test_a101_053.py` alone: 14 passed.

Both failures are pre-existing and unrelated to this port (CLAUDE.md "Known
breaks"): `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this worktree)
and `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
(untracked `docs/pine/` corpus).
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
now passes -- the ledger row is recorded.

## Receipt

Gates A-E clear on the port (hand-derived correctness including the
zero-denominator case, 0/37 causality leaks with the mutant caught at
37/37, bit-identical x8/x64 scale invariance and a disclosed,
measured -- not invented -- 1e-6 tolerance at x10/x3.7, Gate E max \|ρ\|
0.6131 vs `CLV_Pctl` -- well under the 0.76 SHIP line). SHIP; column kept.
