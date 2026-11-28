# Manifest — C22-TREV auto run

**Run folder:** `docs/reviews/auto-2026-11-28-c22-trev/`
**Mode:** C (batch task execution), one free-form task.

## Task

> C22-TREV: port the indicator of issue #263 through Gates A-D, the wiring,
> the tests and docs/<Name>Measured.md, per the issue and the rules in the
> issue-solver system prompt (time-reversal asymmetry of the last 100 daily
> returns: the mean cubed one-bar change of the z-scored window. Positive
> when rises are sharper than falls.). Gate E and the whole suites are run
> by the launcher afterwards.

Source: PandasTa issue #263 (C22-TREV), `CLAUDE.md`'s porting protocol, and
the issue-solver system prompt's rules overriding the issue text (no Gate E
run here, no whole-suite run here).

## Phase 2 — clarify

Checked against the task: indicator name, formula (fully spelled out in the
issue body, including the ddof and NaN rule), default length (100), module
category (`statistics`, matching this fork's other `c22_*` ports), and the
gates owed (A-D, wiring, tests, receipt; E and F's whole-suite run deferred
to the launcher) are all explicit in the issue and the system prompt. No
gaps found — **no clarifying questions needed**.

One judgment call, logged as an ASSUMPTION per the conservative-reading
rule: the issue states "std > 0" as the blanking condition; this port uses
this fork's established `NOISE_ULPS = 4096` floor (9.09e-13) instead of a
literal `> 0`, matching every other catch22-on-returns port in this
repository (`c22_ami2`, `c22_mode_5`, `c22_entropy_pairs`, `c22_dfa`,
`c22_periodicity`) and `CLAUDE.md`'s own description of this as "the
fork's existing habit" for a dimensionless return quantity. A literal
`> 0` would admit noise-dominated flat windows; the floor is the
conservative (narrower-firing) reading and is the one every sibling module
already uses, so diverging here would be the surprising choice, not the
safe one.

## Phase 3 — execution map

Single task, no parallel lanes: implementation on the main thread
(new module + wiring + tests + measurement scripts + receipt), one gate
pass with a Fletcher reviewer subagent.

| task | lane | why |
|---|---|---|
| C22-TREV port | main thread | one indicator, five wiring touch points plus docs — no independent sub-scopes to parallelize |
