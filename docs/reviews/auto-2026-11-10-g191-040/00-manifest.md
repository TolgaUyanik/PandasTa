# Run manifest — auto-2026-11-10-g191-040

## Original ask (verbatim)

> G191-040: port the indicator of issue #77 through Gates A-D, the wiring, the tests and
> docs/<Name>Measured.md, per the issue and the rules in your system prompt (up-volume /
> down-volume ratio (VR). Source: GTJA191 (Guotai Junan 2017 report; HKUDS/Vibe-Trading copy,
> MIT) — `#40: SUM(C>C1 ? V : 0, 26) / SUM(C<=C1 ? V : 0, 26) * 100`.). Gate E and the suites are
> run by the launcher afterwards.

## Mode

`--auto` with a single free-form task description -> Mode C (Batch task execution), one task.
`AskUserQuestion` is unavailable in this headless session (issue-solver rule); Phase 2
clarification is skipped and any ambiguity is resolved by the most conservative reading, logged
as an ASSUMPTION below, per the issue-solver system prompt's override of this skill's own
clarification step.

## Task

| id | scope | source |
|---|---|---|
| g191-040 | Port GTJA191 alpha #40 (up-volume / down-volume ratio) as `pandas_ta/volume/g191_040.py`, Gates A-D, the 5 wiring touch points, `tests/test_g191_040.py`, `docs/G191040Measured.md`. Gate E and both repos' suites are explicitly OUT of this task's scope (run by the issue-solver launcher after this session). | issue #77 (verbatim in the task's args), `CLAUDE.md` porting protocol, `docs/issues/screen/ind_screen.py:350-354` (prototype) |

## Clarifications

None asked (AskUserQuestion unavailable). One ASSUMPTION logged during implementation:

- **ASSUMPTION (bar-0 classification):** the issue's own formula string (`C<=C1 ? V : 0`)
  presumes `C1` is defined. At bar 0 it is not (no prior bar). The issue's own prototype
  (`ind_screen.py:350-354`) resolves this via `v.where(~up, 0.0)`, which — because a comparison
  against `NaN` is `False`, not `NaN` — silently counts bar 0 as a DOWN bar. The conservative
  reading (smaller blast radius: do not fabricate a day's direction from no information) is to
  treat bar 0 as undefined in BOTH buckets instead, matching the warm-up convention this fork's
  `g191_043` already ships. Disclosed in the module docstring, `docs/G191040Measured.md`'s Gate A
  section, and pinned by a dedicated test
  (`tests/test_g191_040.py::test_bar_zero_is_excluded_from_both_buckets_unlike_the_prototype`).

## Execution map

Single task, main thread (not parallelized — one indicator, sequential Gate A-D derivation
requires the judgment calls above; no independent sibling task to pair with in a worktree).

## Destructive / irreversible actions

None required or taken. No force-push, deletion, deploy, or external publish in this task's
scope.

## Two sessions, one run folder (appended 2026-11-11)

The 2026-11-10 session implemented the port and ran review round 1, then stopped on a usage limit
before it could commit; its work was preserved as a WIP commit on `solver-backup/issue-77-g191-040`
(`4bfa0df`, on top of `106195a`, both based on this branch's `19fca14`). A second session on
2026-11-11 restored those files into the worktree, re-ran every measurement and both test runs
from scratch rather than trusting the quoted numbers (all reproduced; see `01-g191-040.md`), then
ran review rounds 2-5 and committed. The run folder keeps its original `auto-2026-11-10-` id so
the manifest, the log and the commit all name the same run.

`ASSUMPTION` (bar-0 classification) above still holds and is unchanged. Round 2 widened it on the
reviewer's finding: the mask now also covers `close.isna()`, so a `NaN` close — where `C > C1`
and `C <= C1` are both `False` — is treated as undefined direction too, rather than having its
volume silently dropped from both buckets while its windows kept firing. Same conservative
reading (do not fabricate a day's direction from no information), applied to both halves of the
comparison instead of one.
