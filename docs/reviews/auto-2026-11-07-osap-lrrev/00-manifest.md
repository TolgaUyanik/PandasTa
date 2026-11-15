# Mode C manifest — osap-lrrev

## Task list (as given)

1. `osap-lrrev` — OSAP-LRREV: port the indicator of issue #35 through Gates A-D, the
   wiring, the tests and `docs/<Name>Measured.md`, per the issue and the rules in the
   issue-solver system prompt (long-run reversal, months t-36..t-13. Source: Open Source
   Asset Pricing SignalDoc (Chen & Zimmermann; US monthly cross-section) —
   `LRreversal (De Bondt-Thaler 1985), OSAP t 3.29`.). Gate E and the suites are run by
   the launcher afterwards.

Source: free-form task string in the `/brutally-honest-review --auto` invocation (not a
TODO tag, not `top-N`). Taken as given per Mode C Phase 1.

## Clarify (Phase 2)

Checked against the issue text (verbatim, in the issue-solver system prompt) and
`docs/issues/screen/ind_screen.py`'s `osap_lrrev` candidate (`delay(c, 252) /
delay(c, 756) - 1`): scope, formula, defaults (252/756 bars) and done-criterion (Gates
A-D + wiring + tests + Measured.md; E/F explicitly deferred to the launcher) are all
stated. No gaps found. **No questions needed.**

## Prior attempt on this issue (context, not a task)

Commit `45aa9ff` ("OSAP-LRREV: port De Bondt-Thaler long-run reversal as osap_lrrev
(momentum). Refs #35") already did this work and PASSed its own Mode C review round 1,
but it is reachable only from `solver-backup/issue-35-osap-lrrev`, based on an older
`dev` tip (`72c7185`) — it is not an ancestor of this branch's current HEAD and is not
on this branch. This session re-derives the same module/tests/docs against current HEAD
(counts differ: `Category` 273 -> 274 now, not 268 -> 269), reusing the prior session's
already-reviewed reasoning and numbers only where they do not depend on the exact
HEAD (the Gate A disclosure, the mutant, the hand-derived example). All new numbers
(README/dictionary/ledger counts, Gate C/D measurements) are re-measured in this
session, not copied.

## Execution map (Phase 3)

Single task, non-parallel, non-overlapping with nothing else running: main thread.
File scope: `pandas_ta/momentum/osap_lrrev.py` (new), `pandas_ta/momentum/__init__.py`,
`pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_osap_lrrev.py` (new),
`README.md`, `docs/IndicatorDictionary.md`, `docs/OsapLrrevMeasured.md` (new),
`docs/measure_osap_lrrev.py` (new), `tests/test_altport2_ports.py`.

## Task file write-back

No detectable status-convention task file in scope: the owner's local tracker
(`docs/issues/`) is a read-only, gitignored copy per the issue-solver rules — never
written. Left alone; noted in `99-summary.md`.
