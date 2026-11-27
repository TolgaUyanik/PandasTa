# Manifest — RD-DIP-DEPTH-10-25 (issue #181)

## Original ask (verbatim)

> RD-DIP-DEPTH-10-25: port the indicator of issue #181 through Gates A-D, the wiring, the tests and
> docs/<Name>Measured.md, per the issue and the rules in your system prompt (dip below the 10-day
> high in average-range units (10, 25). Source: Reddit, tier 4 (ResearchIntel kb/reddit.db):
> rd:algotrading:1rjvxjy (2026-03-03) https://www.reddit.com/r/algotrading/comments/1rjvxj). Gate E
> and the whole suites are run by the launcher afterwards. You and every subagent verify with
> `python -m pytest -q <the port's test modules> tests/test_readme_counts.py
> tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
> tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
> plus any PandasTa test module a finding names, never the whole suite (the launcher runs it). Until
> the launcher's Gate E run and the receipt record this port's ledger row,
> `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` fails: expected, not a
> finding.

## Task list (single task, free-form)

| id | scope | source |
|---|---|---|
| RD-DIP-DEPTH-10-25 | port `rd_dip_depth_10_25` (momentum; `(HHV(high,10)-close)/(SMA(high,25)-SMA(low,25))`) through Gates A-D, wiring, tests, `docs/RdDipDepth1025Measured.md`, per issue #181 and the session's system-prompt rules | user's `--auto` argument, verbatim above |

## Clarify (Phase 2)

Checked: goal, scope and done criterion are all explicit in the issue text and the session's
system-prompt rules (file-change allowlist, Gate E/F deferred to the launcher, exact test command,
category choice left to the port since the issue does not name one). No gap found — **no questions
asked.**

## Execution map (Phase 3)

Single task, no parallel lanes needed (one indicator, touches the standard five wiring points plus
docs — no overlapping-scope conflict to isolate). This port is modeled directly on the fork's own
established shape for a "Reddit crowd-talk ratio of range terms" port: `rd_range_contraction`
(issue #176) and `rd_std_ratio_20_60` (issue #179), both independent-rolling-window ratios with the
same zero-division-to-NaN guard. Run on the **main thread**.

## Destructive/irreversible steps

None attempted. The port only adds new files and makes additive edits to the allowed shared files
(`README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `pandas_ta/__init__.py`,
`pandas_ta/core.py`, `pandas_ta/momentum/__init__.py`, `tests/test_altport2_ports.py`).
