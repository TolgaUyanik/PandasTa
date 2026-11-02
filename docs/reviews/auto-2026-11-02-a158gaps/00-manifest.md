# A158GAPS — batch task execution manifest

**Invocation:** `/brutally-honest-review --auto "A158GAPS: port the indicator of issue #34
through Gates A-D, the wiring, the tests and docs/<Name>Measured.md, per the issue and the
rules in your system prompt (three columns, each over the Alpha158 windows (5, 10, 20, 30,
60):). Gate E and the suites are run by the launcher afterwards."`

**Mode:** C (batch task execution) — the argument is a single free-form task description,
not a plan file and not TODO tags.

## Phase 1 — Select

One resolved task:

| id | scope | source |
|---|---|---|
| A158GAPS | Port `RANK`, `WVMA`, `VSUMD` (qlib Alpha158) through Gates A-D, wiring, tests, `docs/Alpha158Measured.md`. Gate E/suites run by the launcher afterwards. | GitHub issue #34, this session's system prompt |

Run folder: `docs/reviews/auto-2026-11-02-a158gaps/`.

## Phase 2 — Clarify

`AskUserQuestion` is unavailable in this headless issue-solver session (system prompt
rule). Gaps below are resolved by the most conservative (smallest-scope) reading and
logged as ASSUMPTIONs, not asked:

1. **ASSUMPTION — one Category entry per name, five window-columns per call.** The issue's
   "each over the Alpha158 windows (5,10,20,30,60)" is read as one indicator call producing
   a `DataFrame` of five suffixed columns (`RANK_5`..`RANK_60` etc.), not five separate
   single-`length` calls. Smaller-scope reading: this satisfies the "at most 3 new
   `pandas_ta/<category>/*.py` files" cap in one way, where a single-`length` design would
   not (it would need either 15 modules or an awkward multi-instance registration
   `df.ta.strategy()` cannot express). Precedent: `pandas_ta/statistics/trend_scan.py`,
   `pandas_ta/overlap/mmar.py`.
2. **ASSUMPTION — category placement.** `rank` -> `statistics` (shape of `quantile`),
   `wvma` -> `volatility` (shape of `volvol`, a dispersion ratio), `vsumd` -> `volume`
   (shape of `volcv`, volume-only). Documented explicitly as a judgment call in each
   module's docstring per `CLAUDE.md`'s own instruction to do so (`amihud`'s precedent).
3. **ASSUMPTION — Gate E and the ledger stay untouched this session.** Per this session's
   system-prompt override: `docs/gate_e_ledger.csv` gets no new row; the owed-row test
   (`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`) is
   expected to fail locally (it does, for exactly `['rank', 'vsumd', 'wvma']`) and that
   failure is not a defect to fix.

No destructive or irreversible steps are implicated by this task (no force-push, no data
deletion, no deploy) — the hard-limit check in the skill's "Hard limits" section does not
trigger.

## Phase 3 — Plan execution

Single task, no parallel lanes: implemented on the main thread (file scope spans shared
wiring files `pandas_ta/__init__.py`, `pandas_ta/core.py`, three category `__init__.py`
files, and `tests/test_altport2_ports.py`'s pinned totals — overlapping-scope work that a
parallel subagent split would only complicate).

## Phase 4 — Execute + gate

Implementation done on the main thread (see `01-a158gaps.md` for the log and the Fletcher
gate's verdict and rounds).

## Phase 5 — Write-back

`docs/issues/` is a read-only gitignored copy of the owner's local tracker — not writable,
and not in this session's allowed-modify list. No write-back performed; the GitHub issue
itself is the source of truth per its own header, and is not edited by this session
(no `gh` access; the launcher handles the PR).
