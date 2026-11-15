# Manifest — g191_111 (issue #71), 2026-11-10

## Task

Single free-form task, resolved as given:

> G191-111: port the indicator of issue #71 through Gates A-D, the wiring, the tests and
> docs/<Name>Measured.md, per the issue and the rules in your system prompt (volume x
> close-location oscillator. Source: GTJA191 (Guotai Junan 2017 report; HKUDS/Vibe-Trading copy,
> MIT) — `#111: SMA(V*CLV,11,2) - SMA(V*CLV,4,2)`.). Gate E and the suites are run by the
> launcher afterwards.

## Clarification (Phase 2)

Checked: goal, scope, and "done" criterion are all actionable as written. The issue text itself
states the exact source formula and scale-free conversion (`/mean(V,20)`), and the session's own
system prompt states which gates are owed here (A-D, wiring, tests, Measured.md) vs. deferred to
the launcher (Gate E, both repos' suites in clean worktrees). No gaps found; no questions asked.

## Execution map (Phase 3)

Single task, main thread (sequential implementation, no parallel lanes needed): write the
indicator module, wire the five touch points, write `docs/measure_g191_111.py`, write
`tests/test_g191_111.py`, update README/IndicatorDictionary/MLCompanionContract/
test_altport2_ports counts, write `docs/G191111Measured.md`, run the full local suite, commit.

Already implemented and committed before this gate ran (commit `15a6c09`,
"G191-111: port GTJA191 alpha #111 ... Refs #71").
