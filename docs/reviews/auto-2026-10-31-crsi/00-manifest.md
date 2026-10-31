# Manifest — CRSI port (issue #21), Mode C single-task run

## Task

> CRSI: port the indicator of issue #21 through Gates A-D, the wiring, the tests and
> docs/<Name>Measured.md, per the issue and the rules in your system prompt
> (`(RSI(close, 3) + RSI(streak, 2) + PercentRank(1-bar return, 100)) / 3`, where `streak`
> is the signed count of consecutive up or down closes). Gate E and the suites are run by
> the launcher afterwards.

Source: the issue-solver run's system prompt, verbatim (TolgaUyanik/PandasTa#21).

## Clarifications

No AskUserQuestion round: the issue-solver harness for this run disables AskUserQuestion
and instructs taking the most conservative (smaller-scope) reading, logged as an
ASSUMPTION rather than asked. Gaps found and resolved:

| gap | resolution | why conservative |
|---|---|---|
| Issue says "decide whether to ship the composite, the components, or only the streak term, and let Gate E settle it" — but this session cannot run Gate E (launcher runs it afterward) | Ship all three (composite `CRSI_3_2_100`, components `CRSI_STREAK_2` and `CRSI_PCTRANK_100`) now, through Gates A-D only. The ship/revert decision is deferred to a later "receipt session" per the issue-solver system prompt's override rules, which explicitly says Gate E and the final verdict happen after the launcher's run. | Shipping all 3 behind `Category` with Gate E PENDING written into the doc matches the exact precedent this repo already set (`pfe`, `kalman_trend` both merged with Gate E owed) — not a new, larger-scope decision. |
| `RSI(close, 3)` — ship it as its own column, or not? | NOT shipped as a column: it is exactly `ta.rsi(close, 3)`, already available, so shipping it again is a redundant column under CLAUDE.md's non-redundant rule. Computed internally for the composite only. | Smaller surface: one fewer column than a naive transcription of the formula, and the issue's own guess ("probably restates rsi") supports it. |
| `PercentRank` convention: several exist (inclusive/exclusive of current bar, ties counted or not) | Pine's `ta.percentrank`: 100 × (count of the PREVIOUS `n` values strictly less than current) / `n`, ties excluded. Documented explicitly in the module docstring and `CrsiMeasured.md`. | The only convention with a citable, named public definition available without external/web access (web access is unavailable in this session); documented as a design decision rather than asserted as THE Kaufman definition, since Kaufman 2013 was not available on this machine either. |

## Execution map

Single task, main thread (no parallel lanes — one coherent file set: one new indicator
module, its wiring, its tests, its docs). No worktree isolation needed.

## Files touched

- `pandas_ta/momentum/crsi.py` (new)
- `pandas_ta/momentum/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py` (wiring)
- `tests/test_crsi.py` (new), `tests/test_altport2_ports.py` (bumped `CATEGORY_TOTAL`)
- `docs/CrsiMeasured.md` (new), `docs/measure_crsi_proxy.py` (new)
- `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md` (counts)

Gate E, `docs/gate_e_ledger.csv`, and the parent repo's suite are explicitly out of scope
for this session (the launcher's job).
