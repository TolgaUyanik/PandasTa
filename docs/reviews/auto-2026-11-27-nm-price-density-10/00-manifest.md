# Manifest — NM-PRICE-DENSITY-10 (issue #186)

## Original ask (verbatim)

> NM-PRICE-DENSITY-10: port the indicator of issue #186 through Gates A-D, the wiring, the tests and
> docs/<Name>Measured.md, per the issue and the rules in your system prompt (Kaufman's price density
> (10). Source: Kaufman 2013, Trading Systems and Methods 5th ed., ch. 1 'Other Measurements of
> Noise' (ResearchIntel book chunk); named in rd:algotrading:15xt5xt, rd:algotrading). Gate E and the
> whole suites are run by the launcher afterwards. You and every subagent verify with `python -m
> pytest -q <the port's test modules> tests/test_readme_counts.py tests/test_altport2_ports.py
> tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py
> tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py` plus any PandasTa test
> module a finding names, never the whole suite (the launcher runs it). Until the launcher's Gate E
> run and the receipt record this port's ledger row,
> `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` fails: expected, not a
> finding.

## Task list (single task, free-form)

| id | scope | source |
|---|---|---|
| NM-PRICE-DENSITY-10 | port `nm_price_density_10` (volatility; Kaufman's price density, `SUM(H-L, 10) / (MAX(H, 10) - MIN(L, 10))`) through Gates A-D, wiring, tests, `docs/NmPriceDensity10Measured.md`, per issue #186 and the session's system-prompt rules | user's `--auto` argument, verbatim above |

## Clarify (Phase 2)

Checked: goal, scope and done criterion are all explicit in the issue text and the session's
system-prompt rules (file-change allowlist, Gate E/F deferred to the launcher, exact test command).
No ambiguity requiring a question — the issue names exactly one source (Kaufman 2013) and the screen
prototype's own formalisation (`docs/issues/screen/ind_screen_r7.py`'s `nm_price_density_10`) is a
direct transcription of that same chapter formula, disclosed plainly rather than treated as a second
independent derivation. Category resolved to `volatility` (not named by the issue) to match the
closest sibling range/noise-measure indicators already shipped there (`chop` itself lives in `trend`,
but the fork's other range-based noise measures — `pdist`, `donchian`, `inrange_count`,
`rd_range100_pct500`, `rd_range_contraction` — all live in `volatility`, and the issue's own measured
Gate E comparator `chop`/`CHOP` and `EFFICIENCY_RATIO` confirm the same family). No user-facing
gap — **no questions asked.**

## Execution map (Phase 3)

Single task, no parallel lanes needed (one indicator, touches the standard five wiring points plus
docs — no overlapping-scope conflict to isolate). This port is modeled on `nm_effort_result_20`
(issue #185, commit `de29a7b`) for the Measured.md/measure-script template, the `MIN_LENGTH`
forced-constant reasoning, and the future-splice Gate B harness shape, and on `chop`/`pdist` for the
module-level conventions (`verify_series`, rolling-window idiom, `category = "volatility"`). Run on
the **main thread**.

## Destructive/irreversible steps

None attempted. The port only adds new files (`pandas_ta/volatility/nm_price_density_10.py`,
`tests/test_nm_price_density_10.py`, `docs/NmPriceDensity10Measured.md`,
`docs/measure_nm_price_density_10.py`, `docs/measure_nm_price_density_10_cpu.py`) and makes additive
edits to the allowed shared files (`README.md`, `docs/IndicatorDictionary.md`,
`docs/MLCompanionContract.md`, `pandas_ta/__init__.py`, `pandas_ta/core.py`,
`pandas_ta/volatility/__init__.py`, `tests/test_altport2_ports.py`).
