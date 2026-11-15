# Run manifest — G191-167 (issue #68)

## Task

G191-167: port the indicator of issue #68 through Gates A-D, the wiring, the tests and
docs/G191167Measured.md, per the issue and the rules in the session's system prompt. Source:
GTJA191 alpha `#167: SUM(C-C1>0 ? C-C1 : 0, 12)` (12-day sum of up moves). Gate E and both
repos' suites are run by the launcher afterwards, not this session.

Free-form single-task invocation (`--auto "..."`), resolved as Mode C with one task.

## Clarifications

None needed. The task, the formula, the file-scope restrictions and the Gate E/F deferral are
all fully specified in the issue text and the session's system prompt. No AskUserQuestion round
was run (unavailable in this headless session per the rules; conservative reading taken
throughout). No interpretation choice was needed beyond the issue's own string: the ternary
`C-C1>0 ? C-C1 : 0` and `Series.clip(lower=0)` (the issue's own prototype spelling) are the
identical function at every bar including the `C==C1` boundary — measured, not assumed
(`docs/measure_g191_167.py`, `tests/test_g191_167.py::test_clip_matches_an_explicit_ternary_at_the_zero_boundary`).

## Execution map

Single task, main-thread (file-scope restrictions and cross-file wiring conventions need
main-context judgment; not delegated to a parallel subagent).

| task | lane | why |
|---|---|---|
| G191-167 port | main thread | touches 11 files across a fixed allowed-path set, needs line-by-line consistency with existing `g191_*` port conventions |

## Gate

Fletcher reviewer subagent (`Explore`, read-only), dispatched per Mode A steps 3-5, against the
files changed this session (listed in the task report).
