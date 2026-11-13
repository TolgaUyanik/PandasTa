# Run manifest — G191-160 (issue #67)

## Task

G191-160: port the indicator of issue #67 through Gates A-D, the wiring, the tests and
docs/G191160Measured.md, per the issue and the rules in the session's system prompt. Source:
GTJA191 alpha `#160: SMA(C<=C1 ? STD(C,20) : 0, 20, 1)` (down-day volatility EMA). Gate E and
both repos' suites are run by the launcher afterwards, not this session.

Free-form single-task invocation (`--auto "..."`), resolved as Mode C with one task.

## Clarifications

None needed. The task, the formula, the file-scope restrictions and the Gate E/F deferral are all
fully specified in the issue text and the session's system prompt. No AskUserQuestion round was
run (unavailable in this headless session per the rules; conservative reading taken throughout).
One interpretation choice, resolved by matching the issue's own prototype exactly rather than by
guessing: GTJA's `STD` operator uses pandas' default `ddof=1` (sample standard deviation),
matching the convention `g191_076` (issue #54) already established for the identical GTJA `STD`
operator — logged as read-off-the-prototype, not an ASSUMPTION, since the prototype's own
`std(x, n) = x.rolling(n).std()` is unambiguous code, not prose.

## Execution map

Single task, main-thread (file-scope restrictions and cross-file wiring conventions need
main-context judgment; not delegated to a parallel subagent).

| task | lane | why |
|---|---|---|
| G191-160 port | main thread | touches 11 files across a fixed allowed-path set, needs line-by-line consistency with existing `g191_*` port conventions |

## Gate

Fletcher reviewer subagent (`Explore`, read-only), dispatched per Mode A steps 3-5, against the
files changed this session (listed in the task report).
