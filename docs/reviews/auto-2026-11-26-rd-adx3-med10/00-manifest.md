# Manifest — RD-ADX3-MED10 (issue #171)

## Original ask (verbatim)

> RD-ADX3-MED10: port the indicator of issue #171 through Gates A-D, the wiring, the tests and
> docs/<Name>Measured.md, per the issue and the rules in your system prompt (rolling median of
> ADX(3) (10). Source: Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:quant:1gc3o70 (2024-10-25)
> https://www.reddit.com/r/quant/comments/1gc3o70/ — `median over 10 bars of ADX(3)`.). Gate E and
> the whole suites are run by the launcher afterwards. You and every subagent verify with
> `python -m pytest -q <the port's test modules> tests/test_readme_counts.py
> tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
> tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
> plus any PandasTa test module a finding names, never the whole suite (the launcher runs it).
> Until the launcher's Gate E run and the receipt record this port's ledger row,
> `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` fails: expected, not
> a finding.

## Task list (single task, free-form)

| id | scope | source |
|---|---|---|
| RD-ADX3-MED10 | port `rd_adx3_med10` (trend; rolling 10-bar median of ADX(3)) through Gates A-D, wiring, tests, `docs/RdAdx3Med10Measured.md`, per issue #171 and the session's system-prompt rules | user's `--auto` argument, verbatim above |

## Clarify (Phase 2)

Checked: goal, scope and done criterion are all explicit in the issue text and the session's
system-prompt rules (file-change allowlist, Gate E/F deferred to the launcher, exact test command).
No gap found — **no questions asked.**

## Execution map (Phase 3)

Single task, no parallel lanes needed (one indicator, touches the standard five wiring points plus
docs — no overlapping-scope conflict to isolate). Run on the **main thread**.

## Destructive/irreversible steps

None attempted. The port only adds new files and makes additive edits to the allowed shared files
(`README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `pandas_ta/__init__.py`,
`pandas_ta/core.py`, `pandas_ta/trend/__init__.py`, `tests/test_altport2_ports.py`).
