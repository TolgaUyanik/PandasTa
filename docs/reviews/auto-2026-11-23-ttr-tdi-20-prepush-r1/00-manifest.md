# Run manifest — pre-push gate round 1, TTR-TDI-20 (issue #148)

## Task

Fix every CRITICAL and MAJOR finding of the pre-push review gate run against HEAD
`a2989a7bd9a9`, quoted verbatim in the invocation; fix MINOR/NIT only when cheap and
safe. Single free-form task, taken as given (Mode C).

## Clarifications

None needed — findings named exact files and the required fix text.

## Execution map

Single task, overlapping file scope (three files share the MAJOR finding;
`tests/test_altport2_ports.py` also carries a MINOR in the same region) → main thread,
sequential. No parallel lane.

## Gate

Fresh `Explore` subagent, Fletcher persona, read-only. See `01-TTR-TDI-20.md`.
