# Manifest — vol_sign_rev (issue #43, A101-012)

## Task

Single free-form task (Mode C, batch execution with one member):

> A101-012: port the indicator of issue #43 through Gates A-D, the wiring, the tests
> and docs/<Name>Measured.md, per the issue and the rules in the system prompt
> (volume-signed reversal. Source: Alpha101 (Kakushadze 2016, Wilmott; vnpy alpha101
> copy) — `#12: sign(delta(volume,1)) * -delta(close,1)`.). Gate E and the suites are
> run by the launcher afterwards.

## Clarifications

None needed. The issue's own restatement of the formula and its scale-free conversion
(`delta(close,1) -> one-bar return`) were sufficient to implement without ambiguity.
One ASSUMPTION, disclosed in `docs/VolSignRevMeasured.md` and the module docstring:
neither the Kakushadze (2016) paper nor the vnpy `alpha101` repository could be
consulted in this worktree (no web access, `docs/pine/` unavailable), so Gate A rests on
the issue's own restatement, corroborated by the local Gate E screen prototype
(`docs/issues/screen/ind_screen.py:108,212-214`), which computes the identical
expression independently.

## Execution map

One task, main thread (no parallelization needed): implement the module, wire the 5
touch points, write the tests, write the measured-numbers doc, regenerate
`docs/IndicatorDictionary.md`, update `docs/MLCompanionContract.md`'s running SF-tag
count. Gate via one Fletcher reviewer subagent.
