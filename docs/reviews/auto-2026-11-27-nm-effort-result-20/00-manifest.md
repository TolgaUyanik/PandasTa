# Manifest — NM-EFFORT-RESULT-20 (issue #185)

## Original ask (verbatim)

> NM-EFFORT-RESULT-20: port the indicator of issue #185 through Gates A-D, the wiring, the tests and
> docs/<Name>Measured.md, per the issue and the rules in your system prompt (effort vs result:
> relative volume over relative range (20). Source: Wyckoff's 'effort vs result' (volume vs price
> response) as described in rd:Daytrading:1k9oyhh; 'Volume Range Events' (volume change vs candle
> range change) in a round-6 thread (Reddit, tier 4). Gate E and the whole suites are run by the
> launcher afterwards. You and every subagent verify with `python -m pytest -q <the port's test
> modules> tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py
> tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
> tests/test_prose_counts_match_the_csvs.py` plus any PandasTa test module a finding names, never
> the whole suite (the launcher runs it). Until the launcher's Gate E run and the receipt record
> this port's ledger row, `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
> fails: expected, not a finding.

## Task list (single task, free-form)

| id | scope | source |
|---|---|---|
| NM-EFFORT-RESULT-20 | port `nm_effort_result_20` (volume; Wyckoff's effort-vs-result, `[V/SMA20(V)] / [(H-L)/SMA20(H-L)]`) through Gates A-D, wiring, tests, `docs/NmEffortResult20Measured.md`, per issue #185 and the session's system-prompt rules | user's `--auto` argument, verbatim above |

## Clarify (Phase 2)

Checked: goal, scope and done criterion are all explicit in the issue text and the session's
system-prompt rules (file-change allowlist, Gate E/F deferred to the launcher, exact test command).
One disclosed limitation, not a question: the issue's own text states no published formula exists
for this indicator ("this prototype's formalisation: no published formula was found") — so Gate A
cannot derive the port from a second, independent source the way `nm_mmi_250` (issue #184) did.
Resolved conservatively by implementing exactly the issue's own stated expression (identical to the
screen prototype's formalisation) and disclosing this plainly in the module docstring and the
Measured.md, rather than inventing a derivation that does not exist. Category resolved to `volume`
(not named by the issue) to match the three next-closest comparators the issue itself names
(`vol_at_low_ratio`, `VOL_RATIO`, `Volume_Ratio_20`) and the related open issue #19 (`VOLCV`,
also `volume`). No user-facing gap — **no questions asked.**

## Execution map (Phase 3)

Single task, no parallel lanes needed (one indicator, touches the standard five wiring points plus
docs — no overlapping-scope conflict to isolate). This port is modeled on `g191_144` (issue #57) for
its multi-input (`high`/`low`/`volume`) shape, dual-axis (price, volume, combined) Gate D structure,
and future-splice Gate B harness, and on `nm_mmi_250`/`volcv` for the Measured.md template and the
`MIN_LENGTH` forced-constant reasoning. Run on the **main thread**.

## Destructive/irreversible steps

None attempted. The port only adds new files (`pandas_ta/volume/nm_effort_result_20.py`,
`tests/test_nm_effort_result_20.py`, `docs/NmEffortResult20Measured.md`,
`docs/measure_nm_effort_result_20.py`, `docs/measure_nm_effort_result_20_cpu.py`) and makes
additive edits to the allowed shared files (`README.md`, `docs/IndicatorDictionary.md`,
`docs/MLCompanionContract.md`, `pandas_ta/__init__.py`, `pandas_ta/core.py`,
`pandas_ta/volume/__init__.py`, `tests/test_altport2_ports.py`).
