# /brutally-honest-review --auto — manifest (G191-003, issue #79)

**Mode:** C (batch task execution, one task). `--fletcher` on automatically.
No pre-gate: Mode C resolves task references, not a plan carrying
load-bearing reasoning.

**Date:** 2026-11-11 · **Run folder:** `docs/reviews/auto-2026-11-11-g191-003/`

## Phase 1 — resolved task list

| id | scope | source |
|---|---|---|
| G191-003 | Port GTJA191 alpha `#3` (6-day accumulation/distribution sum) through Gates A–D, the five wiring touch points, `tests/test_g191_003.py` and `docs/G191003Measured.md`. Gate E and both repos' suites are run by the issue-solver launcher afterwards. | the `--auto` argument, quoting issue #79 (`docs/issues/078-g191-003.md`, read-only copy in this worktree) |

Source formula, verbatim from the issue:

    #3: SUM(C=C1 ? 0 : C-(C>C1 ? MIN(L,C1) : MAX(H,C1)), 6)

## Phase 2 — clarifications

`AskUserQuestion` is unavailable in this headless session, so every gap was
resolved by the most conservative (smallest-scope) reading and logged as an
ASSUMPTION instead of asked:

* **A1 — category `momentum`.** The formula reads close/high/low and no
  volume, so `volume` is wrong; `momentum` is where the fork's other
  price-only GTJA191 ports live (`g191_002`, `g191_129`). Smaller scope
  than inventing a category.
* **A2 — one column, `G191_003_6`.** The fixed `6` is exposed as
  `length=6`, this fork's convention for every other GTJA191/Alpha101
  port. No second column, no `raw=` variant.
* **A3 — scale-free via `/close`**, the issue's own `conv` field for this
  candidate. Not a percent (`*100`), because the prototype does not.
* **A4 — the merged variant `g191_029` ships nothing.** Issue #79 merges
  it in as a near-restatement (prototype ρ 0.9077); porting it too would
  widen the issue's scope.
* **A5 — Gate E is not run here**, per the session rules: the launcher
  runs `gate_e_overlap.py`, and this session never reads `../Backtesting`.
  `docs/G191003Measured.md` carries Gate E as pending and
  `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  fails by design ("Owed, not failed", CLAUDE.md).
* **A6 — the pre-existing `Category`-mutation bug found while running test
  subsets is NOT fixed here.** `pandas_ta/core.py:692` calls `.remove` on
  the live list returned by `_indicators_by_category` (`core.py:453`).
  Fixing it changes `strategy()` behaviour, which is outside issue #79.
  Disclosed at the end of `docs/G191003Measured.md`.
* **A7 — no `docs/gate_e_ledger.csv` row is written**, since there is no
  run to record. A later receipt session records it.

## Phase 3 — execution map

Single task, **main thread**. No parallel subagent lane: the work is one
indicator touching five wiring points plus two docs, all overlapping
scope, and it needs main-context judgment (Gate A readings, which numbers
to measure). Worktree isolation would buy nothing.

Review gate: one Fletcher reviewer subagent (`Explore`, read-only) per
round, up to 3 REVISE rounds, then ESCALATE.

## Files in scope

* `pandas_ta/momentum/g191_003.py` (new)
* `pandas_ta/momentum/__init__.py`, `pandas_ta/__init__.py`,
  `pandas_ta/core.py` (wiring)
* `tests/test_g191_003.py` (new), `tests/test_altport2_ports.py`
  (`CATEGORY_TOTAL`)
* `docs/measure_g191_003.py`, `docs/G191003Measured.md` (new)
* `README.md`, `docs/IndicatorDictionary.md` (regenerated),
  `docs/MLCompanionContract.md`
* this run folder
