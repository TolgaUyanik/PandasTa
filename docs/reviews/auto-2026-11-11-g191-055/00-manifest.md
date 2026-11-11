# Run manifest — auto-2026-11-11-g191-055

**Mode:** C (batch task execution, `--auto` with a free-form task reference)
**Date:** 2026-11-11
**Repo / branch:** `PandasTa-80-g191-055` / `issue-80-g191-055`
**Reviewer:** fresh read-only `Explore` subagent per round, Fletcher persona ON
(Mode C turns `--fletcher` on automatically)

## Task

One task, resolved from the invocation's own text (not from a `TODO.md` tag —
this repo's tracker is `docs/issues/`, which is gitignored):

| id | scope | source |
|---|---|---|
| `g191-055` | Port issue #80's GTJA191 alpha `#55` (20-day Wilder swing-index sum) through Gates A–D, wire it at all five touch points, write `tests/test_g191_055.py` and `docs/G191055Measured.md`. Gate E and both repos' suites are the launcher's. | the `/brutally-honest-review --auto "G191-055: …"` invocation, which quotes issue #80 |

## Phase 2 — Clarify

**No questions asked.** `AskUserQuestion` is unavailable in this headless
session, and the governing rules say to take the most conservative reading
(smaller scope) and log it. Four decisions were taken that way:

* **ASSUMPTION 1 — category `momentum`.** A swing-index sum is a directional
  momentum accumulation, and the fork's nearest ports (`g191_093` DBM sum,
  `g191_187` DTM sum) are both `momentum`. This is also the smaller-blast-radius
  choice: `tests/test_altport2_ports.py`'s `CATEGORY_BUCKETS` tracks only
  `trend`/`volatility`/`volume`, so `momentum` moves one pinned integer
  (`CATEGORY_TOTAL`) instead of two.
* **ASSUMPTION 2 — the THREE-branch `R`.** The issue's quote of the formula is
  elided and its prototype's `R` has two branches; the report's own string (as
  recalled, no copy readable here) has three. Issue #80 says "Gate A starts from
  the source formula, not the prototype", so the three-branch form ships, the
  recall is labelled as recall, and the size of the divergence is measured three
  ways. Full argument: `docs/G191055Measured.md`, Gate A.
* **ASSUMPTION 3 — `length=20` exposed as a tunable** rather than hard-coded,
  this fork's convention for every other GTJA191/Alpha101 port.
* **ASSUMPTION 4 — the bar-0 mask is declarative, and says so.** The arithmetic
  alone already lands NaN at bar 0; the explicit `.where(...)` is kept for the
  reading, not claimed to be load-bearing.

## Phase 3 — Execution map

| task | lane | why |
|---|---|---|
| `g191-055` | main thread | single task, needs main-context judgement (the two-versus-three-branch Gate A call), and it edits shared pinned files (`pandas_ta/__init__.py`, `core.py`, `README.md`, `tests/test_altport2_ports.py`) that a parallel worktree lane would only have to merge back |

No parallel lanes, no worktree isolation. The review gate was never skipped.

## Destructive steps

None. Nothing in this task force-pushes, deletes data, deploys, or publishes.
The branch is committed, never pushed — the launcher pushes.
