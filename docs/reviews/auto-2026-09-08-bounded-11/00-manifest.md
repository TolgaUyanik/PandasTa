# 00 — Manifest: bounded-11 batch (Mode C)

Invocation: `/brutally-honest-review --auto @PandasTa/TODO.md`
Run folder: `docs/reviews/auto-2026-09-08-bounded-11/`

## Phase 2 — clarifications (the ONE permitted round)

| question | answer |
|---|---|
| Routing: file path (Mode B) vs tagged tasks (Mode C) | **Mode C** — one escalation does not kill the batch |
| Scope: all 14 open tasks? | **Bounded 11.** Defer PINEBI-2, INDREF-1, MLCOL-1 — each is a session, not a batch member |
| `pandas_ta.rma` is not Wilder's smoothing; `atr`/`natr` inherit it | **Document only, do not change.** Add a Wilder variant ALONGSIDE; `rma`/`atr` stay byte-identical |

### Why the rma answer matters to this batch

`natr` feeds a live paper-trading rule (`ML_Position: natr > 3.11`) under the
2026-07-27 trading freeze, and mined rules match on exact column values. So the
correction ships as a NEW callable and every Pine port that needs Wilder's
smoothing calls it explicitly. Nothing downstream moves. This is prerequisite
work for the Pine ports and is executed first, logged as **RMA-W**.

## Tasks (11)

| # | task | scope |
|---|---|---|
| 1 | RMA-W (prereq, owner-directed this round) | Wilder variant alongside `rma` |
| 2 | PINEBI-1e | 4 ML utilities: `sum`, `pivot`, `normalize`, `covariance` |
| 3 | PINEBI-1d | 2 lower-timeframe requests, capability-checked |
| 4 | PINEBI-1c | 9 alternates: measure, keep only what differs |
| 5 | PINEBI-1b | 16 `port` rows |
| 6 | TALIB-1 | 10 rows: BETA, HT_DCPERIOD, HT_DCPHASE, HT_PHASOR, HT_SINE, HT_TRENDLINE, HT_TRENDMODE, IMI, MAMA, SAREXT |
| 7 | CANDLE-0 | pattern shortlist + non-duplication proof |
| 8 | CANDLE-1 | implement shortlist (depends CANDLE-0) |
| 9 | CANDLE-2 | settle the TA-Lib question |
| 10 | INDREF-0 | page template on one indicator |
| 11 | MLCOL-2 | prove companions carry signal the parent does not |

Deferred by owner: **PINEBI-2, INDREF-1, MLCOL-1**.

## ASSUMPTIONS (logged, not asked — Phase 2 is closed)

1. **INDREF-2 is dropped from the bounded set.** It `depends on INDREF-1`, which
   the owner deferred, and its "done when" requires linking back to per-indicator
   pages that will not exist. Conservative reading, smaller blast radius. It was
   in neither the recommended option's list nor reachable; saying so here rather
   than half-doing it.
2. **CANDLE-0's premise is stale and is corrected, not obeyed.** It states "TA-Lib
   is not installed in this environment, so its ~60 patterns are unreachable".
   Measured this run: `ta.cdl_pattern(..., name="all")` returns **62 pattern
   columns** against talib 0.7.1. CANDLE-0's non-duplication proof must therefore
   run against 62 reachable patterns, not against zero — this makes the task
   HARDER, not easier, so it is not a scope reduction.
3. **CANDLE-2 is largely answered by that same measurement** and becomes: pin the
   62 as tested-and-reachable, or declare the dependency optional. It is not
   skipped.
4. **Gate E measurements land in `../Backtesting/scripts/analysis/`** per the port
   protocol. That is analysis only — it does not touch `deploy/`, so the trading
   freeze is not engaged.

## Execution map

All porting tasks write the same five wiring touch points — notably
`pandas_ta/__init__.py` (`Category`) and `pandas_ta/core.py`. Parallel lanes
would collide there on every task, and merging five worktrees through those two
files is a worse risk than running serially. So:

| lane | tasks | why |
|---|---|---|
| parallel subagents | CANDLE-0, INDREF-0, MLCOL-2 | disjoint scopes, no wiring edits |
| main thread, sequential | RMA-W → PINEBI-1e → -1d → -1c → -1b → TALIB-1 | all share `Category` + `core.py` |
| main thread, after CANDLE-0 | CANDLE-1, CANDLE-2 | dependency + shared docs |

## Standing constraints carried into every task

- `docs/pine` is **untracked on purpose** (912 files MPL-2.0 © TradingView, root
  LICENSE MIT). Do not commit it. Each library port carries MPL attribution in its
  module docstring; `kcw` and `stc` are core built-ins and carry none.
- No sibling repo may be committed into this one.
- Never import `pandas_ta_classic` in-process — 109 failures. Subprocess only.
- Trading freeze (owner, 2026-07-27) on `deploy/`: untouched by this batch.
- Every claim containing *only/never/always/every/all* or a count must correspond
  to a run. That defect is the reason this repo's review rounds exist.
