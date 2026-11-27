# Manifest — NM-MMI-250 (issue #184)

## Original ask (verbatim)

> NM-MMI-250: port the indicator of issue #184 through Gates A-D, the wiring, the tests and
> docs/<Name>Measured.md, per the issue and the rules in your system prompt (Market Meanness Index
> of daily returns (250). Source: Johann Christian Lotter, 'The Market Meanness Index',
> financial-hacker.com; named in rd:algotrading:hr30er (Reddit, tier 4) — `MMI = 100*(nl + nh)).
> Gate E and the whole suites are run by the launcher afterwards. You and every subagent verify
> with `python -m pytest -q <the port's test modules> tests/test_readme_counts.py
> tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
> tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
> plus any PandasTa test module a finding names, never the whole suite (the launcher runs it). Until
> the launcher's Gate E run and the receipt record this port's ledger row,
> `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` fails: expected, not a
> finding.

## Task list (single task, free-form)

| id | scope | source |
|---|---|---|
| NM-MMI-250 | port `nm_mmi_250` (statistics; Lotter's Market Meanness Index, `100*(nl+nh)/(n-1)`, applied to 250 daily simple returns) through Gates A-D, wiring, tests, `docs/NmMmi250Measured.md`, per issue #184 and the session's system-prompt rules | user's `--auto` argument, verbatim above |

## Clarify (Phase 2)

Checked: goal, scope and done criterion are all explicit in the issue text and the session's
system-prompt rules (file-change allowlist, Gate E/F deferred to the launcher, exact test command).
One open question the issue itself leaves to the port: the issue states the formula in Zorro's own
array order (`Data[0]` most recent, higher index older) without translating it — resolved
conservatively by deriving the translation into this fork's forward-chronological convention from
first principles in the module docstring (documented reasoning, not asserted), rather than copying
the screen prototype's own array-indexing choice uncritically. Category is left to the port since
the issue does not name one; resolved to `statistics`, matching this fork's placement of every
other rolling-window "share/count of a return-window property" port (`c22_high_fluctuation`,
`lean_hurst_100`, `stability`). No user-facing gap — **no questions asked.**

## Execution map (Phase 3)

Single task, no parallel lanes needed (one indicator, touches the standard five wiring points plus
docs — no overlapping-scope conflict to isolate). This port is modeled directly on
`c22_high_fluctuation` (issue #144) for its windowed-returns-with-sliding_window_view shape and
MIN_LENGTH degenerate-constant reasoning, and on `rd_quadfit_resid_20`/`rd_range_contraction` for
the Measured.md and measure-script template. Run on the **main thread**.

## Destructive/irreversible steps

None attempted. The port only adds new files (`pandas_ta/statistics/nm_mmi_250.py`,
`tests/test_nm_mmi_250.py`, `docs/NmMmi250Measured.md`, `docs/measure_nm_mmi_250.py`,
`docs/measure_nm_mmi_250_cpu.py`) and makes additive edits to the allowed shared files
(`README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `pandas_ta/__init__.py`,
`pandas_ta/core.py`, `pandas_ta/statistics/__init__.py`, `tests/test_altport2_ports.py`).
