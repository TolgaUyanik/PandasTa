# Manifest — C22-RS-RANGE pre-push gate fix round

Invocation: `/brutally-honest-review --auto "Fix every CRITICAL and MAJOR finding of the
pre-push review gate (round 1 of 3, HEAD 939de55741c7)..."` with the full gate
contract quoted in the prompt.

## Task

One task, free-form (not a TODO tag): apply every CRITICAL/MAJOR finding from the
quoted pre-push gate verdict (REVISE) against `docs/measure_c22_rs_range.py` and
`docs/C22RsRangeMeasured.md`, and fix MINOR/NIT findings where cheap and safe.

## Clarification

None needed — the gate contract gave file:line locations and concrete fixes for
every finding; no ambiguity required a question.

## Execution map

Single task, single file-scope pair (`docs/measure_c22_rs_range.py`,
`docs/C22RsRangeMeasured.md`), sequential — main thread. No parallel lane: the
findings are entangled (the harness's SEARCH output numbers feed directly into the
receipt's table), so a split would just recreate the same dependency by hand.

## Scope note (logged ASSUMPTION)

Round 1 finding #1's fix also suggested re-scoping a sentence in
`docs/measure_c22_ami2.py` ("the only part of this repository that runs the
reference implementation") now that a second harness (this one) also calls
`pycatch22`. That file is a pre-existing module from issue #127, outside this
issue's allowed-file list (`docs/measure_*.py` may only be ADDED as new files,
not modified). Conservative reading: left untouched. Logged here, not asked,
per the batch-mode rule (mid-run ambiguity resolved to the smaller-scope
reading).
