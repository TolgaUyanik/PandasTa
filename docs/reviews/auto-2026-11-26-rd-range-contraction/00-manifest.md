# Mode C manifest — rd-range-contraction

## Resolved task

Single free-form task, taken as given (verbatim from the invocation):

> RD-RANGE-CONTRACTION: port the indicator of issue #176 through Gates A-D, the wiring, the
> tests and docs/<Name>Measured.md, per the issue and the rules in the system prompt (short
> over long average of the 5-bar high-low spread (10, 50). Source: Reddit, tier 4
> (ResearchIntel kb/reddit.db): rd:algotrading:dejh73 (2019-10-07)
> https://www.reddit.com/r/algotrading/comments/dej). Gate E and the whole suites are run by
> the launcher afterwards. Verify with
> `python -m pytest -q <the port's test modules> tests/test_readme_counts.py
> tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
> tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
> tests/test_prose_counts_match_the_csvs.py` plus any PandasTa test module a finding names,
> never the whole suite. `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
> failing is expected, not a finding.

Run folder: `docs/reviews/auto-2026-11-26-rd-range-contraction/`

## Phase 2 — clarify

No AskUserQuestion round: the tool is unavailable in this headless session (issue-solver's own
rule), and the formula, parameters (n=5, short=10, long=50) and scale-free form ("as a ratio")
are all stated in the issue text, so there is no genuine gap to ask about.

**ASSUMPTION** (most conservative / smallest-scope reading, logged per the issue-solver rules
rather than asked): the issue's "Prototype... as a ratio" line is read as `MA(spread, short) /
MA(spread, long)` (the exact screen-prototype formula,
`docs/issues/screen/ind_screen_r6.py`'s `rd_range_contraction`), not the poster's "cross over"
language, since the issue itself frames the prototype's ratio as the port's own scale-free form
and Gate A is required to cite the issue's restatement, not the poster's words, for the formula.

## Phase 3 — plan execution

One task, no parallel lanes (nothing to split: a single module + its wiring + its test file +
its receipt doc form one dependency chain). Executed on the main thread.

## Execution

Already implemented and committed (commit `6d18ee6`) before this gate ran:

- `pandas_ta/volatility/rd_range_contraction.py` (new module)
- `pandas_ta/volatility/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py` (wiring)
- `tests/test_rd_range_contraction.py` (new, 21 tests: Gate A correctness, Gate B
  mutant/causality, Gate D scale-free, Gate C reachability, wiring)
- `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 402→403, `CATEGORY_BUCKETS["volatility"]`
  39→40)
- `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md` (counters)
- `docs/RdRangeContractionMeasured.md` (receipt; Gate E recorded as pending per the
  issue-solver's own rules)
- `docs/measure_rd_range_contraction.py`, `docs/measure_rd_range_contraction_cpu.py`
  (measurement scripts, incl. the CPU-feature-disabled re-run)

Required test command, run after every change in this session:

```
python -m pytest -q tests/test_rd_range_contraction.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py \
    tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py \
    tests/test_prose_counts_match_the_csvs.py
```

Last run: 1,623 passed, 7 skipped, 1 failed (`test_gate_e_ledger.py::test_every_indicator_that
_needs_a_row_has_one` — expected, owed until the launcher's Gate E run).
