# Run manifest — G191-109 (issue #76)

**Task (as given):** G191-109: port the indicator of issue #76 through Gates A-D, the wiring,
the tests and `docs/<Name>Measured.md`, per the issue and the rules in the session system
prompt (range EMA over its own EMA (single mass-index ratio). Source: GTJA191 (Guotai Junan
2017 report; HKUDS/Vibe-Trading copy, MIT) — `#109: SMA(H-L,10,2) / SMA(SMA(H-L,10,2),10,2)`.).
Gate E and the suites are run by the launcher afterwards.

**Clarifications:** none needed. The task text, the issue body, and this worktree's CLAUDE.md
fully specify scope, formula, gate table, and the Gate E/F deferral to the launcher.

**Execution map:** single task, main thread (no parallel lanes — one indicator module touching
a fixed, small set of files per the issue-solver's allowed-paths list).

**Files touched:**
- `pandas_ta/volatility/g191_109.py` (new module)
- `pandas_ta/volatility/__init__.py` (export)
- `pandas_ta/__init__.py` (`Category["volatility"]`)
- `pandas_ta/core.py` (`AnalysisIndicators.g191_109` accessor)
- `tests/test_g191_109.py` (new test suite, 17 tests)
- `docs/measure_g191_109.py` (new, independent-measurement script)
- `docs/G191109Measured.md` (new, receipt)
- `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 310->311, `CATEGORY_BUCKETS["volatility"]` 31->32)
- `README.md` (headline 310->311 / 318->319, volatility row)
- `docs/IndicatorDictionary.md` (regenerated)
- `docs/MLCompanionContract.md` (tag-count sentence + note, 655->656 / 298->299 `SF`)
