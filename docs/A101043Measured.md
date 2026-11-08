# a101_043 — measured (issue #46)

> **Status: Gates A-D cleared. Gate E: pending, run by issue-solver after
> this session.** Gate F (both repos' suites) is run by the launcher in
> clean worktrees; `python -m pytest -q` in this worktree is reported below
> for the record.

Relative-volume rank x 7-day reversal rank: Kakushadze's (2016, Wilmott, "101
Formulaic Alphas") Alpha101 `#43`, per issue #46's own instruction. Module
`pandas_ta/momentum/a101_043.py`, column `A101_043_20_20_7_8`. Tests:
`tests/test_a101_043.py` (19, all passing). Numbers below:
`python docs/measure_a101_043.py`. Environment: this worktree's pinned
pandas/numpy. Measured 2026-11-08.

## Gate A: derivation from the published formula, not the prototype

Issue #46 states Alpha101 `#43`:

    ts_rank(volume/adv20, 20) * ts_rank(-delta(close, 7), 8)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web access
are both unavailable in this worktree, so the issue's own named copy -- vnpy's
`vnpy/alpha101` module (MIT) -- was never read. Everything below is derived from
the issue's own stated formula and from this fork's already-established
conventions, not from vnpy or from Kakushadze's original paper text directly.

Two operators in the formula carry an unstated convention and are resolved as
**ASSUMPTIONs, disclosed, not independently confirmed against vnpy**:

1. `adv(d)`. Kakushadze's glossary defines `adv(d)` as the average DAILY DOLLAR
   volume (price times volume) over the past `d` days, not plain share volume.
   This fork already resolved the identical ambiguity for `a101_021` (issue
   #45, `docs/A101021Measured.md`) by reading `adv(d)` as a plain volume
   rolling mean, because the issue's own prototype
   (`docs/issues/screen/ind_screen.py`'s `relv(v, n=20): return sdiv(v, mean(v,
   n))`) and its own disclosed "unchanged under price x8" invariant both
   require a volume-only `adv` -- a dollar-volume `adv` would carry a price
   term and break that invariant. The same reasoning applies here: for the
   whole expression to be scale-free in `close` independently of `volume` (see
   SCALE-FREE below), `adv20` must carry no price term at all. Reused for
   internal consistency with `a101_021`, not independently re-derived from
   vnpy. This session's own Gate D run below reproduces the invariant on this
   port (bit-identical under price x8/x64/x10/x3.7), corroborating the reading.
2. `ts_rank(x, d)`. Kakushadze's glossary names the operator but does not
   spell out tie handling or the exact normalisation; this fork already ships
   two operators under this exact convention -- `pandas_ta.statistics.rank`'s
   `RANK_d = count(close[t-d+1..t] <= close[t]) / d` for qlib's `Rank`, and
   `pandas_ta.volume.a101_058`'s own `_ts_rank` for Alpha101 `#58` (issue #42)
   -- so the same convention (`count(window <= current) / d`) is reused here
   for internal consistency, not independently re-derived from vnpy. The
   helper is duplicated locally inside `a101_043.py` rather than imported,
   matching `a101_058`'s own choice (CLAUDE.md: import a helper from its own
   module, never from another module or the package).

No other operator needs resolution: `delta(x, d) = x - x.shift(d)` is read
directly off the formula string, and the trailing `*` is a plain pointwise
product of the two ranks.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | primary vnpy/Kakushadze text NOT consulted (no `docs/pine/`/web this session) -- self-consistent against the issue's own stated formula, with two disclosed ASSUMPTIONs (`adv(d)` as plain volume rolling mean, reused from `a101_021`; `ts_rank` as `count(window <= current) / d`, reused from `a101_058`) argued above from this fork's own prior resolutions of the identical ambiguities | 6-bar hand-derived example at `adv_length=2, vol_rank_length=2, delta_length=2, rev_rank_length=2` (`tests/test_a101_043.py::test_hand_derived_six_bars`), reproduced in `docs/measure_a101_043.py` (`hand-derived bars 0..5: [nan, nan, nan, 0.25, 1.0, 0.25]`). Matches an independent per-bar loop built from plain Python (not pandas' `.rolling()`/`sliding_window_view`) at the shipped defaults (`adv_length=20, vol_rank_length=20, delta_length=7, rev_rank_length=8`), 3 spot-checked bars (100, 500, 899) on a 900-bar synthetic walk |
| B Causality | pass | Future-perturbation sweep (close and volume both rewritten from `j` onward), 35 offsets past the 38-bar warm-up: real module **0 of 35** leaks (`python docs/measure_a101_043.py`). A weaker mutant was tried first and rejected as a quantisation artefact of `ts_rank`'s bucketed output, not a causality gap: a 1-bar look-ahead on `d7` alone is a real look-ahead (proved live: output differs from the real module) but caught only **25 of 35** -- `ts_rank`'s output absorbs a 1-bar perturbation often enough at this window size to miss it at 10 of the 35 offsets. The mutant actually shipped shifts the whole write index `rev_rank_length=8` bars into the future (`result = (vrank * revrank).shift(-rev_rank_length)`, `importlib` source read, `exec`'d in memory): shown live (differs from the real module), then caught at **35 of 35** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic walk (seed 11, sigma=1.5%/bar close, sigma=1.95%/bar volume), shipped defaults: **1,462 of 1,500** bars non-NaN (97.47%) -- exactly `n - 38`, the `max(adv_length+vol_rank_length-2, delta_length+rev_rank_length-1) = 38`-bar warm-up, no wider gap. **104 distinct values** observed on this walk (not a constant column, and well short of the `20*8=160` cells the two rank grids could in principle populate) |
| D Scale-free | pass | x8/x64 on EITHER close OR volume independently: **bit-identical, 0.0 max\|diff\|** (`relvol` never reads `close`; `-d7`/`revrank` never read `volume`; `ts_rank` is an order statistic invariant to a positive rescale of its own input). x10/x3.7 on either input: **also 0.0 max\|diff\|**, exact rather than merely within the 1e-9 tolerance the test asserts -- no tie-breaking or floating-point drift flips a rank bucket on this 1,500-bar walk. `0 < 1,462 fires < 1,500` and `104 > 1` distinct values rule out a constant column |
| E Attribution | pending, run by issue-solver after this session | -- |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **278 → 279** (`momentum` **66 → 67**); `df.ta.<name>()` accessor count
**286 → 287**. Touch points: `pandas_ta/momentum/a101_043.py` (module),
`pandas_ta/momentum/__init__.py` (export), `pandas_ta/__init__.py` →
`Category["momentum"]` (discovery), `pandas_ta/core.py` →
`AnalysisIndicators.a101_043` (accessor), `tests/test_a101_043.py` (tests).
`README.md`'s headline and `momentum (67)` row, and `docs/IndicatorDictionary.md`
(regenerated), both updated and checked by `tests/test_readme_counts.py`.
`docs/MLCompanionContract.md`'s running tag count updated **623 → 624 / 266 → 267
`SF`** (`A101_043_20_20_7_8` probes cleanly at the dictionary's 600-bar synthetic
frame and takes many distinct values in (0, 1], so the generator tags it `SF`);
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`
re-derives and passes against the updated `Counter`. `tests/test_altport2_ports.py`'s
`CATEGORY_TOTAL` updated to match (278 → 279); `CATEGORY_BUCKETS` is unaffected
(it tracks only `trend`/`volatility`/`volume`, not `momentum`).

`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` fails
in this worktree until the launcher's Gate E run is recorded -- expected, per
this session's instructions ("Gate E owed", CLAUDE.md).

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order: **3 failed, 4315
passed, 83 skipped**. All three failures are expected and unrelated to the
port's own logic: `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this worktree),
`test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` (CLAUDE.md
"Known breaks" -- untracked `docs/pine/` corpus), and
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (Gate E
owed for `a101_043`, exactly as this session's rules require). No other test
regresses; `tests/test_a101_043.py` alone: 19 passed.

Note: `tests/test_wiring_accessors.py`'s `strategy()`-exercising tests mutate
the module-level `Category` lists in place (`core.py`'s `strategy()` calls
`[ta.remove(x) for x in excluded if x in ta]` on the live list returned by
`_indicators_by_category`, not a copy) -- a pre-existing defect, not
introduced by this port. It only surfaces if that test module is collected
before `tests/test_readme_counts.py` in the same process; alphabetical
collection order (the default, and `tests/test_altport2_ports.py`'s letter
precedes both) avoids it, which is why the full-suite run above is clean.

## Receipt

Gates A-D clear on the port. Gate E is pending; the launcher runs it after
this session, and a later receipt session records the measured max |rho| here
and in `docs/gate_e_ledger.csv`, deciding SHIP vs. a measured revert.
