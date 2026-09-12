# Auto-run manifest — SHOWCASE batch

- **Run:** 2026-09-12, Mode C (batch task execution), `--fletcher` on
- **Invocation:** `/brutally-honest-review --auto SHOWCASE-0 SHOWCASE-1 SHOWCASE-2 SHOWCASE-3 SHOWCASE-4 SHOWCASE-5`
- **Task source:** `PandasTa/TODO.md`, `## SHOWCASE` block (lines 146-224)

## Tasks resolved

| id | scope | source line |
|---|---|---|
| SHOWCASE-0 | scope doc: publish / synthesise / drop per block, owner-signed | `TODO.md:160` |
| SHOWCASE-1 | all 16 broken `INDICATOR_SPECS` arg lists correct + a test asserting zero swallowed exceptions | `TODO.md:174` |
| SHOWCASE-2 | no bare `except:`; failures collected, reported, and reflected in exit status | `TODO.md:187` |
| SHOWCASE-3 | exercise the fork's own indicators; coverage count printed by the example AND asserted by a test | `TODO.md:194` |
| SHOWCASE-4 | no network, no `deploy/` import, `yfinance` optional; `tests/test_showcase.py` green offline | `TODO.md:206` |
| SHOWCASE-5 | land it; README links it; suite stays 0 failed | `TODO.md:214` |

## Prior state (measured 2026-09-12, before this run)

`examples/speedy_analysis.ipynb` was built earlier the same day and audited against these
criteria. Result: **1 of 6 fully met** (SHOWCASE-2). Gaps carried into this run:

- no `docs/SHOWCASE_SCOPE.md` (SHOWCASE-0 never closed; the build started anyway)
- 13 of 16 broken specs present — `long_run`, `short_run`, `trend_return` absent (each needs a
  derived series, not a plain OHLCV column)
- no test of any kind; coverage count printed but unasserted
- Hilbert family 2 of 7; `hwc` never called; MLCOL-1 companions present in frames but never named
- README has 0 references to the example

## Clarifications (Phase 2, the only questions in this run)

| question | answer |
|---|---|
| Scoring layer: drop entirely, or synthesise neutral demo constants per SHOWCASE-0's written default? | **Keep it dropped.** No composite score, thresholds or BULLISH/BEARISH verdict anywhere. Scope doc records `drop`, overriding the task's own default proposal. |
| Split between the notebook and the new example file? | **Script carries everything; notebook stays unchanged.** `examples/market_dashboard.py` becomes the complete tested reference; `speedy_analysis.ipynb` remains the narrative tour. |
| What does `tests/test_showcase.py` cover? | **Script only.** No new test dependencies; the notebook stays untested prose-with-outputs. |

## Execution map

All six tasks are **main-thread, sequential**. No parallel subagent lanes.

Reason: SHOWCASE-1, -2, -3 and -4 all write to the same two files
(`examples/market_dashboard.py`, `tests/test_showcase.py`), so their file scopes overlap
completely — the skill's parallel-lane condition (non-overlapping scope) is not met. SHOWCASE-0
gates the rest by its own terms. SHOWCASE-5 depends on the artifacts 1-4 produce.

| task | lane | why |
|---|---|---|
| SHOWCASE-0 | main | blocking gate; IP judgement, not mechanical |
| SHOWCASE-1 | main | writes `examples/market_dashboard.py` |
| SHOWCASE-2 | main | same file |
| SHOWCASE-3 | main | same file + `tests/test_showcase.py` |
| SHOWCASE-4 | main | same two files |
| SHOWCASE-5 | main | depends on 1-4 landing first |

## Assumptions logged during execution

Recorded in each task's own log file as they arise. No further questions after this point.
