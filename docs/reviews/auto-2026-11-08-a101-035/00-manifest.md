# Manifest — auto run 2026-11-08-a101-035

## Invocation

`/brutally-honest-review --auto "A101-035: port the indicator of issue #50 through
Gates A-D, the wiring, the tests and docs/<Name>Measured.md, per the issue and the rules
in your system prompt (volume rank x price rank x return rank. Source: Alpha101
(Kakushadze 2016, Wilmott; vnpy alpha101 copy) — `#35: ts_rank(volume,32) *
(1-ts_rank(close+high-low,16)) * (1-ts_rank(returns,32))`.). Gate E and the suites are
run by the launcher afterwards."`

Mode: C (batch task execution) — single free-form task, taken as given.

## Tasks

| id | scope | source |
|---|---|---|
| a101-035 | Port Alpha101 `#35` as `a101_035` through Gates A-D, wiring, tests, `docs/A101035Measured.md`. Gate E and both repos' suites are the launcher's job, not this session's. | the invocation argument, verbatim |

## Phase 2 — clarify

No gaps: the task's goal, scope and "done" criterion are fully specified by the issue
text and the overriding rules already present in this session's system prompt (which
files may be touched, that Gate E must be left "pending, run by issue-solver after this
session", that the suites are run here only for this repo). No questions needed.

## Phase 3 — execution map

Single task, main thread (no parallel lane needed — one task, no other work to
schedule against it).

| task | lane | why |
|---|---|---|
| a101-035 | main thread | sole task; needs main-context judgment (category placement, `ts_rank`/`returns` convention choice, mutant design) |
