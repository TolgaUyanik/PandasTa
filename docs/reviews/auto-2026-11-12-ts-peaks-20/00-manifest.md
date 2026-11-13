# Run manifest — `/brutally-honest-review --auto` (Mode C), TS-PEAKS-20

**Date:** 2026-11-12 (the run crossed midnight into 2026-11-13; the folder
keeps its start date)
**Branch:** `issue-92-ts-peaks-20`
**Invocation:** `/brutally-honest-review --auto "TS-PEAKS-20: port the
indicator of issue #92 through Gates A-D, the wiring, the tests and
docs/<Name>Measured.md, per the issue and the rules in your system prompt
(confirmed local peaks of close (20, support 2). Source: tsfresh
feature_calculators (MIT) — `number_peaks(x, n=2) on 20 closes; a peak counts
once confirmed 2 bars later`.). Gate E and the suites are run by the launcher
afterwards."`

Mode routing: `--auto` plus a free-form TASK reference → **Mode C, batch task
execution** (one task). Mode C has no refutation pre-gate by design.

## Task list (Phase 1)

| id | scope | source |
|---|---|---|
| ts-peaks-20 | port tsfresh `number_peaks(x, n=2)` over 20 closes as `ts_peaks_20` (statistics) through Gates A–D, five wiring touch points, tests, `docs/TsPeaks20Measured.md` | PandasTa issue #92, local tracker copy `docs/issues/091-ts-peaks-20.md`, prototype `docs/issues/screen/ind_screen.py` candidate `ts_peaks_20` |

Run folder: `docs/reviews/auto-2026-11-12-ts-peaks-20/`.

## Clarifications (Phase 2)

**None asked — `AskUserQuestion` is unavailable in this headless session.** The
governing rule is "take the most conservative reading (the smaller scope) and
log it as an ASSUMPTION". Five readings the issue's wording leaves open were
decided that way, and each is *priced* with a measurement in
`docs/TsPeaks20Measured.md` §A5 rather than asserted:

* **ASSUMPTION 1 — `n = 2` means both sides at distances 1 AND 2** (the
  source's `for i in range(1, n + 1)`), not only "the close two bars later".
  Conservative because it is the published `number_peaks`, and the issue's own
  prototype spells exactly those four comparisons. Price of the alternatives:
  Spearman 0.767425 (far-distance only) and 0.115928 (support 1) on a walk.
* **ASSUMPTION 2 — the comparison is strict `>`**, so a plateau is not a peak.
  Price: bit-equal to `>=` on a continuous walk, Spearman −0.098358 on a
  coarse grid where 51.74% of candidates tie.
* **ASSUMPTION 3 — the window is 20 CLOSES (16 candidates)**, not 20
  candidates. Price: 0.791649.
* **ASSUMPTION 4 — the output is the raw COUNT**, the source's `np.sum`, not
  the share. Price: an exact rescaling, Spearman 1.000000, so invisible to a
  rank miner either way.
* **ASSUMPTION 5 — one new module, one column, no extras.** `length` is the
  only parameter; the support 2 is a module constant and appears in the column
  name `TS_PEAKS_20_2`. The smaller scope: no second column, no `troughs=`
  flag, no normalisation option.

Two further decisions forced by the session's rules, not by the issue:

* **Gate E is not run here.** `docs/TsPeaks20Measured.md` says "Gate E:
  pending, run by issue-solver after this session"; no row was added to
  `docs/gate_e_ledger.csv`, so
  `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  fails locally and names `['mtd_ret', 'ts_peaks_20']`. That is the expected
  "owed, not failed" state.
* **The indicator is wired into `Category` anyway**, not held out to silence
  that test.

## Execution map (Phase 3)

Single task, **main thread**: the work is one indicator plus eight files that
all touch the same counts (`README.md`, `docs/IndicatorDictionary.md`,
`docs/MLCompanionContract.md`, `tests/test_altport2_ports.py`), so there is no
non-overlapping scope to fan out and nothing to isolate in a worktree.

The review gate is a fresh read-only `Explore` subagent per round, Fletcher
persona on, with the original ask verbatim and the explicit file list. Five
rounds ran; the log is `01-ts-peaks-20.md`, the summary `99-summary.md`.
