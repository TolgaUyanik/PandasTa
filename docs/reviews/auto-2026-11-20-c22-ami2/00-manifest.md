# Auto run c22-ami2 — 2026-11-20

`/brutally-honest-review --auto` (Mode C, batch task execution, `--fletcher`
on). One task, run on the main thread, gated by a fresh read-only Fletcher
reviewer after each state.

## Tasks

| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | C22-AMI2 | GitHub [#127](https://github.com/TolgaUyanik/PandasTa/issues/127), mirrored at `docs/issues/126-c22-ami2.md` | Port catch22's 5-bin automutual information of the last 100 daily returns at lag 2 through Gates A–D, the five wiring touch points, `tests/test_c22_ami2.py` and `docs/C22Ami2Measured.md`. Gate E and both repos' suites are the launcher's. |

## Clarifications (asked ONCE, before execution)

None asked: this is a headless issue-solver session, `AskUserQuestion` is
unavailable, and the session's own rules say to take the most conservative
reading of any ambiguity and log it as an ASSUMPTION. The three that came up
are in `01-c22-ami2.md`'s execution log.

## Execution map

| Task | Lane | Why |
|------|------|-----|
| C22-AMI2 | main thread | one task; the module, its wiring, its tests and four documents all touch each other, so there is no non-overlapping file scope to parallelise, and every number in the documents has to come from a harness run made in the same context |

## Gate

Fresh `Explore` (read-only) subagent per round, Fletcher persona, given: the
original ask verbatim, the session's binding rules (Gate E owed; "a claim
written before it was measured" is the repo's dominant defect; CI-CPU
stability; the GPL-3.0 boundary), the file list, and — from round 2 on — the
previous round's findings with what was done about each. Each reviewer re-ran
the harness and the suites itself rather than reading the tables.

Round cap: the project's review rule is round 1 plus up to three re-runs, and
"not PASS after round 4 → stop and report the open findings". That is what
happened; see `99-summary.md`.
