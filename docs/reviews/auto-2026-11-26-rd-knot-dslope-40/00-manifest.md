# Auto run manifest — rd-knot-dslope-40

**Task (verbatim, from the invocation):** RD-KNOT-DSLOPE-40: port the indicator of issue #175
through Gates A-D, the wiring, the tests and docs/<Name>Measured.md, per the issue and the
rules in the issue-solver system prompt (slope change at the best one-knot spline break (40).
Source: Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:smxy8i (2022-02-07)
https://www.reddit.com/r/algotrading/comments/smxy8i/ — "hinge coefficient of the lowest-MSE
one-knot fit"). Gate E and the whole suites are run by the launcher afterwards.

## Phase 2 — clarify

No gaps needing a question: the issue fully specifies the formula (via its own restatement
of the poster's words plus the screen prototype's disclosed window/knot-range choice), the
module/category convention is fixed by the sibling port `rd_knot_pos_40` (issue #166, same
Reddit post, same knot search, already in `pandas_ta/statistics/`), and the issue-solver
system prompt fixes Gate E/F handling (pending / launcher-run). No AskUserQuestion round
needed. One ASSUMPTION logged below.

**ASSUMPTION (conservative reading, smaller scope):** placed the new module in the
`statistics` category, matching its mathematical sibling `rd_knot_pos_40` (#166), rather than
`trend` (which the issue's prose motivation — "locate where a trend changes slope" — might
also suggest). Smaller-blast-radius reading: follows an existing, already-reviewed precedent
exactly rather than introducing a new placement judgment call.

## Phase 3 — execution map

Single task, no parallel opportunity: implemented on the main thread, in the order the
protocol requires (module -> wiring -> tests -> docs -> counters), each file inside the
Files-you-may-change allowlist. No worktree isolation needed (no concurrent agents touching
these files).

## Phase 4 — gate

One Fletcher reviewer subagent dispatched against the complete diff (see `01-rd-knot-dslope-40.md`
for the round log and verdict).
