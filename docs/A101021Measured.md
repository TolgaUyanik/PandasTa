# a101_021 — measured (issue #45)

> **Status: Gates A-D cleared this session. Gate E: pending, run by issue-solver
> after this session.** Gate F (both repos' suites) is run by the launcher in
> clean worktrees; `python -m pytest -q` in this worktree is reported below for
> the record.

Mean/std band regime with volume tiebreak: Kakushadze's (2016, Wilmott, "101
Formulaic Alphas") Alpha101 `#21`, per issue #45's own instruction. Module
`pandas_ta/momentum/a101_021.py`, column `A101_021_8_2_20`. Tests:
`tests/test_a101_021.py` (18, all passing). Numbers below:
`python docs/measure_a101_021.py`. Environment: this worktree's pinned
pandas/numpy. Measured 2026-11-08.

## Gate A: derivation from the published formula, not the prototype

Issue #45 states Alpha101 `#21`:

    (mean8+std8 < mean2) ? -1 : (mean2 < mean8-std8 ? 1 : (volume/adv20 >= 1 ? 1 : -1))

**What this session could NOT do, disclosed up front:** `docs/pine/` and web access
are both unavailable in this worktree, so the issue's own named copy -- vnpy's
`vnpy/alpha101` module (MIT) -- was never read. Everything below is derived from
the issue's own stated formula and from this fork's already-established
conventions, not from vnpy or from Kakushadze's original paper text directly.

Two operators in the formula carry an unstated convention and are resolved as
**ASSUMPTIONs, disclosed, not independently confirmed against vnpy**:

1. `stddev(x, d)`. Kakushadze's glossary names the operator but, per the issue's
   own restatement (the only source available this session), does not spell out
   its degrees-of-freedom convention. No other Alpha101 port already shipped in
   this fork (`a101_048`, `a101_058`) establishes a `stddev` precedent to reuse.
   This port uses pandas' own rolling-std default, `ddof=1` -- the same reading
   the issue's own prototype takes (`docs/issues/screen/ind_screen.py`'s
   `std(x, n): return x.rolling(n).std()`, plain pandas, no override). This is
   **not** Pine's `ta.stdev(biased=true)` convention (`ddof=0`, per CLAUDE.md's
   Gate A table) -- that convention names a Pine source, and Alpha101 is not one.
2. `adv(d)`. Kakushadze's glossary defines `adv(d)` as the average DAILY DOLLAR
   volume (price times volume) over the past `d` days, not plain share volume.
   But the issue's own disclosed pre-flight measurement states the prototype
   column is "unchanged under price ×8" -- true only if `adv20` carries no price
   term at all, since a price-scaled dollar-volume `adv20` would change the
   `volume/adv20` ratio under a pure price rescale and could flip the tiebreak
   branch on some bars, contradicting that disclosed invariant. Reading `adv(d)`
   as a plain volume rolling mean -- the issue's own prototype's convention,
   `docs/issues/screen/ind_screen.py`'s `relv(v, n=20): return sdiv(v, mean(v,
   n))` -- is the only reading consistent with the issue's own disclosed
   invariant, so it is adopted here. It also matches this fork's own existing
   use of the name: `pandas_ta.volume.maxvol_adv`'s `ADV = volume.rolling
   (long).mean()` is already plain share volume, not dollar volume, under
   this exact acronym. This session's own Gate D run below reproduces the
   issue's disclosed invariant on this port (bit-identical under price
   ×8/×64/×10/×3.7 on the synthetic walk measured), corroborating the
   reading rather than merely assuming it.

No other operator needs resolution: `mean(x, d)` is the plain rolling mean, and
the comparisons/ternary structure is read directly off the formula string.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | primary vnpy/Kakushadze text NOT consulted (no `docs/pine/`/web this session) -- self-consistent against the issue's own stated formula, with two disclosed ASSUMPTIONs (`stddev` ddof=1, `adv(d)` as plain volume rolling mean) argued above from the issue's own prototype and its own disclosed price-invariance measurement | 9-bar hand-derived example at `length=3, fast_length=1, adv_length=2` hitting all three branches (bars 2-4 tiebreak +1, bar 5 branch1 -1, bars 6-7 tiebreak -1, bar 8 branch2 +1), computed by hand from the formula text (`tests/test_a101_021.py::test_hand_derived_nine_bars_all_three_branches`). Matches an independent per-bar loop built from plain Python `statistics.mean`/`statistics.stdev` (not pandas `.rolling()`) at the shipped defaults (`length=8, fast_length=2, adv_length=20`), 3 spot-checked bars (100, 250, 399) on a 400-bar synthetic walk |
| B Causality | pass | Future-perturbation sweep (close and volume both rewritten from `j` onward), 35 offsets past the 20-bar warm-up: real module **0 of 35** leaks (`python docs/measure_a101_021.py`). Two weaker mutants were tried first and rejected as quantisation artefacts of the discretised `{-1, 1}` output, not causality gaps: a 1-bar look-ahead on `s8` alone caught only **8 of 35**, and shifting the whole write index by `length=8` bars caught **32 of 35** -- in both cases the regime decision at most offsets sits far enough from its own decision boundary that a small perturbation does not flip the sign, so a real leak goes undetected. The mutant actually shipped shifts the whole write index `adv_length=20` bars into the future (`result = result.where(mask).shift(-adv_length)`, `importlib` source read, `exec`'d in memory): shown live (differs from the real module), then caught at **35 of 35** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic walk (seed 11, σ=1.5%/bar close, σ=1.95%/bar volume), shipped defaults: **1,481 of 1,500** bars non-NaN (98.73%) -- exactly `n - 19`, the `max(length, fast_length, adv_length) - 1 = 19`-bar warm-up, no wider gap. Exactly **2 distinct values**, by construction (`-1.0`: 718 bars, `1.0`: 763 bars) -- both regimes fire, not a constant column |
| D Scale-free | pass | x8/x64 on EITHER close OR volume independently: **bit-identical, 0.0 max\|diff\|** (every comparison in the formula is between two terms scaled identically by a positive rescale of the one input it reads). x10/x3.7 on either input: **also 0.0 max\|diff\|**, exact rather than merely within the 1e-9 tolerance the test asserts -- no floating-point drift anywhere in the chain flips a branch on this 1,500-bar walk. `0 < 1,481 fires < 1,500` and both `{-1.0, 1.0}` present rule out a constant column |
| E Attribution | **pending, run by issue-solver after this session** | — |
| F Suites | this repo only; parent repo (`Backtesting`) and Gate E are run by the launcher in clean worktrees | `python -m pytest -q` (this session): **3 failed, 4289 passed, 83 skipped** -- all three failures pre-existing/expected and unrelated to this port: `test_pine_coverage_csv.py` (known break, untracked `docs/pine/` corpus -- see CLAUDE.md "Known breaks"), `test_altrepo_talib_csv.py` (needs the sibling `../AlternativeRepos` checkout), `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (Gate E owed for this port, expected until the launcher's run is recorded) |

## Wiring

`Category` **277 → 278** (`momentum` **65 → 66**); `df.ta.<name>()` accessor count
**285 → 286**. Touch points: `pandas_ta/momentum/a101_021.py` (module),
`pandas_ta/momentum/__init__.py` (export), `pandas_ta/__init__.py` →
`Category["momentum"]` (discovery), `pandas_ta/core.py` →
`AnalysisIndicators.a101_021` (accessor), `tests/test_a101_021.py` (tests).
`README.md`'s headline and `momentum (66)` row, and `docs/IndicatorDictionary.md`
(regenerated), both updated and checked by `tests/test_readme_counts.py`.
`docs/MLCompanionContract.md`'s running tag count updated **622 → 623 / 103 → 104
`BIN`** (`A101_021_8_2_20` probes cleanly at the dictionary's 600-bar synthetic
frame and takes only the two values -1/1, so the generator tags it `BIN`);
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`
re-derives and passes against the updated `Counter`. `tests/test_altport2_ports.py`'s
`CATEGORY_TOTAL` updated to match (277 → 278); `CATEGORY_BUCKETS` is unaffected
(it tracks only `trend`/`volatility`/`volume`, not `momentum`).

`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails in this worktree, as expected per CLAUDE.md's "Owed, not failed": no
ledger row exists yet for `a101_021`. The launcher's `GATE_E_PENDING_OK=1` run
treats this as a skip, not a failure; a later receipt session records the row
once Gate E has run.

## Receipt

Gate E has not run yet. This session cleared Gates A-D and the wiring/tests;
Gate E is run by the launcher after this session, and a later receipt session
will fill in the measured numbers here and in `docs/gate_e_ledger.csv`,
deciding ship vs. revert per CLAUDE.md's Gate E bands.
