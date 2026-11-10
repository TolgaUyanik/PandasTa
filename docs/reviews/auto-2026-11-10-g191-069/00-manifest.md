# Run manifest — G191-069 port (issue #70)

**Mode:** C (batch task execution), single free-form task — ambiguous mode selection per the
skill's routing table (the `--auto` argument is a free-form task description, not a plan/spec
file path and not a TODO tag), resolved to the smaller-scope reading since AskUserQuestion is
unavailable in this headless session (ASSUMPTION, logged here per the skill's conservative-
reading rule).

## Task

> G191-069: port the indicator of issue #70 through Gates A-D, the wiring, the tests and
> docs/<Name>Measured.md, per the issue and the rules in the session's system prompt (open-based
> directional balance (DTM/DBM, 20). Source: GTJA191 — #69: SUM(DTM,20) vs SUM(DBM,20) normalised
> by the larger; DTM = O<=O1 ? 0 : MAX(H-O, O-O1)). Gate E and the suites are run by the launcher
> afterwards.

## Phase 2 — clarify

No gaps needing a user question: the issue text, the session's system prompt (gate table, file
scope, commit convention) and two prior `g191_*` ports in this fork (`g191_043`, `g191_098`)
already fully specify scope, formula and "done" criterion. One disclosed ASSUMPTION was needed
inside the implementation itself (not a scope question): the issue states `DTM` in full but names
`DBM` only by its mirror role, so this port takes `DBM`'s exact shape from the issue's own cited
prototype (`docs/issues/screen/ind_screen.py:408-416`) — recorded in `docs/G191069Measured.md`'s
Gate A section, not re-litigated here.

## Phase 3 — execution map

Single task, main thread (no parallel lanes — one coherent change touching wiring files that
must stay consistent with each other).

| Task | Lane | Why |
|---|---|---|
| Port `g191_069` (Gates A-D, wiring, tests, docs) | main thread | File scope spans `pandas_ta/__init__.py`, `pandas_ta/core.py`, `pandas_ta/trend/__init__.py`, README.md and docs — all must move together; no independent subtask to parallelize |
