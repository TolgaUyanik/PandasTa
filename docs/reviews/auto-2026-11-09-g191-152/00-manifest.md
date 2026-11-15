# Run manifest — G191-152 (issue #66)

## Task

G191-152: port the indicator of issue #66 through Gates A-D, the wiring, the tests and
docs/G191152Measured.md, per the issue and the rules in the session's system prompt. Source:
GTJA191 alpha `#152: SMA(MEAN(DELAY(SMA(DELAY(C/C9,1),9,1),1),12) - MEAN(same,26), 9, 1)`. Gate E
and both repos' suites are run by the launcher afterwards, not this session.

Free-form single-task invocation (`--auto "..."`), resolved as Mode C with one task.

## Clarifications

None needed. The task, the formula, the file-scope restrictions and the Gate E/F deferral are all
fully specified in the issue text and the session's system prompt. No AskUserQuestion round was
run (unavailable in this headless session per the rules; conservative reading taken throughout,
logged as ASSUMPTION where applicable in `docs/G191152Measured.md`).

## Execution map

Single task, main-thread (file-scope restrictions and cross-file wiring conventions need
main-context judgment; not delegated to a parallel subagent).

| task | lane | why |
|---|---|---|
| G191-152 port | main thread | touches 10 files across a fixed allowed-path set, needs line-by-line consistency with existing `g191_*` port conventions |

## Gate

Fletcher reviewer subagent (`Explore`, read-only), dispatched per Mode A steps 3-5, against the
files changed this session (listed in the task report).
