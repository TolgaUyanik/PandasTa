# Run manifest — RD-OBV-DEV5 (issue #177)

## Task (verbatim, as given)

> RD-OBV-DEV5: port the indicator of issue #177 through Gates A-D, the wiring, the tests and
> docs/<Name>Measured.md, per the issue and the rules in the system prompt (OBV minus its 5-bar SMA,
> over average volume. Source: Reddit, tier 4 (ResearchIntel kb/reddit.db):
> rd:algotrading:14rriwv (2023-07-05) https://www.reddit.com/r/algotrading/comments/14rriwv/ —
> `OBV vs SMA(OBV, 5)`). Gate E and the whole suites are run by the launcher afterwards. Verify with
> `python -m pytest -q tests/test_rd_obv_dev5.py tests/test_readme_counts.py
> tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
> tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
> plus any PandasTa test module a finding names, never the whole suite. Until the launcher's Gate E
> run and the receipt record this port's ledger row, `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
> fails: expected, not a finding.

## Mode

`--auto` with a single free-form task description → Mode C (batch task execution), treated as a
one-task batch.

## Phase 2 — clarify

Checked for gaps: the issue's "What" line and its own parenthetical fully fix the formula
(`(OBV - SMA5(OBV)) / SMA20(volume)`), the window (5) and the denominator window (20); the scope
question (poster's two-part ADX+OBV condition vs. this port's OBV-only column) is resolved by the
issue's own "What" line, which names only the OBV side. No ambiguity requiring a question.
**ASSUMPTION** (conservative reading, smaller scope): ship only the OBV-vs-its-SMA distance as the
column; do not also encode the poster's ADX>40 leg, since that is a different, already-shipped
indicator (`adx`) and combining the two is a strategy decision for the parent repo, not a feature
column.

## Phase 3 — execution map

One task, main thread (no parallel lanes: single indicator, sequential Gate A→D→wiring→tests→docs
dependency chain, no file-scope overlap with any other task).

## Files touched

New: `pandas_ta/volume/rd_obv_dev5.py`, `tests/test_rd_obv_dev5.py`, `docs/measure_rd_obv_dev5.py`,
`docs/measure_rd_obv_dev5_cpu.py`, `docs/RdObvDev5Measured.md`.
Modified: `pandas_ta/volume/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`,
`tests/test_altport2_ports.py`, `README.md`, `docs/MLCompanionContract.md`,
`docs/IndicatorDictionary.md` (regenerated).
