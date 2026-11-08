# a101_007 — measured (issue #51)

> **Status: Gates A-E cleared on the port -- SHIP (DISCLOSE band).** Gate E
> max|ρ| 0.7681 vs `vol_at_low_ratio`, under the 0.80 DISCLOSE_GAP line and
> well under the 0.90 STRUCK line, so the column ships with this disclosure.
> Gate F (both repos' suites) is run by the launcher in clean worktrees;
> `python -m pytest -q` in this worktree is reported below for the record.

Volume-gated 7-day move rank: Kakushadze's (2016, Wilmott, "101 Formulaic
Alphas") Alpha101 `#7`, per issue #51's own instruction. Module
`pandas_ta/momentum/a101_007.py`, column `A101_007_20_7_60`. Tests:
`tests/test_a101_007.py` (19, all passing). Numbers below:
`python docs/measure_a101_007.py`. Environment: this worktree's pinned
pandas/numpy. Measured 2026-11-08.

## Gate A: derivation from the published formula, not the prototype

Issue #51 states Alpha101 `#7`:

    adv20<volume ? -ts_rank(|delta(close,7)|,60)*sign(delta(close,7)) : -1

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy --
vnpy's `vnpy/alpha101` module (MIT) -- was never read. Everything below is
derived from the issue's own stated formula and from this fork's already-
established conventions, not from vnpy or from Kakushadze's original paper
text directly.

Two operators in the formula carry an unstated convention and are resolved as
**ASSUMPTIONs, disclosed, not independently confirmed against vnpy**:

1. `adv(d)`. Kakushadze's glossary defines `adv(d)` as the average DAILY
   DOLLAR volume (price times volume) over the past `d` days, not plain share
   volume. This fork already resolved the identical ambiguity for `a101_021`
   (issue #45, `docs/A101021Measured.md`) and `a101_043` (issue #46,
   `docs/A101043Measured.md`) by reading `adv(d)` as a plain volume rolling
   mean, because the issue's own prototype
   (`docs/issues/screen/ind_screen.py`'s `relv(v, n=20): return sdiv(v, mean(v,
   n))`) and its own disclosed "unchanged under price x8" invariant both
   require a volume-only `adv` -- a dollar-volume `adv` would carry a price
   term and break that invariant for any formula that compares `adv` directly
   against `volume`. The same reasoning applies here: for the `adv20<volume`
   gate to stay unchanged under a pure price rescale (see SCALE-FREE below),
   `adv20` must carry no price term at all. Reused for internal consistency
   with `a101_021`/`a101_043`, not independently re-derived from vnpy. This
   session's own Gate D run below reproduces the invariant on this port
   (bit-identical under price x8/x64/x10/x3.7 AND volume x8/x64/x10/x3.7),
   corroborating the reading.
2. `ts_rank(x, d)`. Kakushadze's glossary names the operator but does not
   spell out tie handling or the exact normalisation; this fork already ships
   this convention under the same name in `pandas_ta.statistics.rank`'s
   `RANK_d`, `pandas_ta.volume.a101_058`'s own `_ts_rank` and
   `pandas_ta.momentum.a101_043`'s own `_ts_rank` -- so the same convention
   (`count(window <= current) / d`) is reused here for internal consistency,
   not independently re-derived from vnpy. The helper is duplicated locally
   inside `a101_007.py` rather than imported, matching those ports' own
   choice (CLAUDE.md: import a helper from its own module, never from another
   module or the package).

No other operator needs resolution: `delta(x, d) = x - x.shift(d)` and
`sign(x)` (`numpy.sign`) are read directly off the formula string.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | primary vnpy/Kakushadze text NOT consulted (no `docs/pine/`/web this session) -- self-consistent against the issue's own stated formula, with two disclosed ASSUMPTIONs (`adv(d)` as plain volume rolling mean, reused from `a101_021`/`a101_043`; `ts_rank` as `count(window <= current) / d`, reused from `a101_043`/`a101_058`) argued above from this fork's own prior resolutions of the identical ambiguities | 7-bar hand-derived example at `adv_length=2, delta_length=2, ts_rank_length=2` (`tests/test_a101_007.py::test_hand_derived_seven_bars`), reproduced in `docs/measure_a101_007.py` (`hand-derived bars 0..6: [nan, nan, nan, -1.0, 0.5, -1.0, -1.0]`), exercising both the gated branch (bars 4 and 6) and the flat `-1` fallback (bars 3 and 5). Matches an independent per-bar loop built from plain Python (not pandas' `.rolling()`/`sliding_window_view`) at the shipped defaults (`adv_length=20, delta_length=7, ts_rank_length=60`), 3 spot-checked bars (100, 500, 899) on a 900-bar synthetic walk |
| B Causality | pass | Future-perturbation sweep (close and volume both rewritten from `j` onward), 35 offsets past the 66-bar warm-up: real module **0 of 35** leaks (`python docs/measure_a101_007.py`). A weaker mutant was tried first and rejected as a quantisation artefact, not a causality gap: a 1-bar look-ahead on `d7` alone is a real look-ahead (proved live: output differs from the real module) but caught only **17 of 35** -- `ts_rank`'s bucketed output and the flat `-1` fallback branch both absorb a 1-bar perturbation often enough to miss it at 18 of the 35 offsets. The mutant actually shipped shifts the whole write index `ts_rank_length=60` bars into the future (`result = result.where(mask).shift(-ts_rank_length)`, `importlib` source read, `exec`'d in memory): shown live (differs from the real module), then caught at **35 of 35** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic walk (seed 11, sigma=1.5%/bar close, sigma=1.95%/bar volume), shipped defaults: **1,434 of 1,500** bars non-NaN (95.60%) -- exactly `n - 66`, the `max(adv_length, delta_length+ts_rank_length) - 1 = 66`-bar warm-up, no wider gap. **120 distinct values** observed on this walk (not a constant column), range `[-1.0, 1.0]`, median `-0.983333` (the flat `-1` fallback branch dominates on this walk) |
| D Scale-free | pass | x8/x64 on EITHER close OR volume independently: **bit-identical, 0.0 max\|diff\|** (`tsrank`/`sign` never read `volume`; the `volume > adv` gate never reads `close`; `ts_rank` is an order statistic invariant to a positive rescale of its own input, and the strict inequality `volume > adv` keeps its truth value under a positive common rescale of both sides). x10/x3.7 on either input: **also 0.0 max\|diff\|**, exact rather than merely within the 1e-9 tolerance the test asserts -- no tie-breaking or floating-point drift flips a rank bucket or a gate decision on this 1,500-bar walk. `0 < 1,434 fires < 1,500` and `120 > 1` distinct values rule out a constant column |
| E Attribution | **DISCLOSE (ships)** | Launcher's Gate E run (`is51-a101_007-ba8c9803`, 2026-11-09), column `A101_007_20_7_60`, 89 ALTPORT-1 BIST frames, 392,975 pooled bars, 687 comparators (329 `compute_all` + 358 manifest): max\|ρ\| **0.7681** vs `vol_at_low_ratio` (compute_all, n=392,975); per-frame max median\|ρ\| **0.7635**, 0.0% of frames ≥ 0.90. Pooled max also checked against the manifest set alone: 0.7681 vs `Volume_Ratio_20` (n=392,965). Canary bit-equal on AKBNK/BIENY/AGHOL/SASA. In the 0.76-0.80 DISCLOSE band per CLAUDE.md's Gate E table -- ships with this disclosure, not STRUCK (pooled and per-frame-median both well under 0.90). Matches the issue's 2026-10-24 prototype screen (max\|ρ\| 0.7686 vs `VOL_RATIO`/`Volume_Ratio_20`/`vol_at_low_ratio`, per-frame max median 0.7626) within measurement noise. Recorded in `docs/gate_e_ledger.csv` |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **285 → 286** (`momentum` **70 → 71**); `df.ta.<name>()` accessor
count **293 → 294**. Touch points: `pandas_ta/momentum/a101_007.py` (module),
`pandas_ta/momentum/__init__.py` (export), `pandas_ta/__init__.py` →
`Category["momentum"]` (discovery), `pandas_ta/core.py` →
`AnalysisIndicators.a101_007` (accessor), `tests/test_a101_007.py` (tests).
`README.md`'s headline and `momentum (71)` row, and `docs/IndicatorDictionary.md`
(regenerated), both updated and checked by `tests/test_readme_counts.py`.
`docs/MLCompanionContract.md`'s running tag count updated **630 → 631 / 273 → 274
`SF`** (`A101_007_20_7_60` probes cleanly at the dictionary's 600-bar synthetic
frame and takes many distinct values in [-1, 1], so the generator tags it `SF`);
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`
re-derives and passes against the updated `Counter`. `tests/test_altport2_ports.py`'s
`CATEGORY_TOTAL` updated to match (285 → 286); `CATEGORY_BUCKETS` is unaffected
(it tracks only `trend`/`volatility`/`volume`, not `momentum`).

`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails until the launcher's Gate E run is recorded in `docs/gate_e_ledger.csv`
-- expected per CLAUDE.md ("Owed, not failed"); a later receipt session
records the row once the launcher's run lands.

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order: **3 failed, 4489
passed, 83 skipped**. `a101_007`'s own Gate E ledger row is now recorded
(above), so its ledger test passes; the three failures are unrelated to this
port (CLAUDE.md "Known breaks" plus one pre-existing owed row for a
different, already-merged indicator):
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (owed
for `mtd_ret`, unrelated to this issue -- merged separately, pre-dates this
session), `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this worktree)
and `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
(untracked `docs/pine/` corpus). No other test regresses;
`tests/test_a101_007.py` alone: 19 passed.

## Receipt

Gate E run by the launcher 2026-11-09 (`is51-a101_007-ba8c9803`), recorded in
`docs/gate_e_ledger.csv` by this receipt session. Verdict DISCLOSE: max\|ρ\|
0.7681 vs `vol_at_low_ratio`, in the 0.76-0.80 band, under the 0.90 STRUCK
line. The port ships -- no column removed.
