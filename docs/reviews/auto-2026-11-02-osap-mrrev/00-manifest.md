# Run manifest — osap-mrrev (issue #37)

## Task

Single free-form task (Mode C, one task), from the issue-solver's command invocation:

> OSAP-MRREV: port the indicator of issue #37 through Gates A-D, the wiring, the tests
> and docs/<Name>Measured.md, per the issue and the rules in your system prompt
> (medium-run reversal, months t-18..t-13. Source: Open Source Asset Pricing SignalDoc
> (Chen & Zimmermann; US monthly cross-section) — `MRreversal, OSAP t-stat not given`.).
> Gate E and the suites are run by the launcher afterwards.

## Clarification (Phase 2)

AskUserQuestion is unavailable in this headless session (issue-solver rule). No gaps
needed clarification: the issue, `CLAUDE.md`'s porting protocol, and the sibling port
`osap_lrrev` (issue #35, same formula shape `close.shift(near)/close.shift(far)-1`,
read via `git show 45aa9ff` since that branch is not yet merged into this one) gave a
complete, unambiguous template. No ASSUMPTION beyond what the module docstring and
`docs/OsapMrrevMeasured.md` already disclose (the 252/378-bar month-to-trading-day
conversion, taken from the issue/prototype, not independently re-derived — primary OSAP
SignalDoc unavailable in this worktree).

## Execution map

One task, main thread (wiring touches 6+ shared files sequentially; not parallelizable
against itself).

| step | file(s) | lane |
|---|---|---|
| module | `pandas_ta/momentum/osap_mrrev.py` | main thread |
| export | `pandas_ta/momentum/__init__.py` | main thread |
| discovery | `pandas_ta/__init__.py` (`Category["momentum"]`) | main thread |
| accessor | `pandas_ta/core.py` | main thread |
| tests | `tests/test_osap_mrrev.py` | main thread |
| measure script | `docs/measure_osap_mrrev.py` | main thread |
| receipt | `docs/OsapMrrevMeasured.md` | main thread |
| counts | `README.md`, `docs/IndicatorDictionary.md` (regenerated), `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py` | main thread |

## Gate

Fletcher reviewer subagent (Explore, read-only) dispatched against the full file list
below, per Mode C Phase 4.
