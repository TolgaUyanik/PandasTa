# Run summary — c22-stretch-high (2026-11-22)

| Task | Status | Rounds | Files touched | Follow-ups |
|------|--------|--------|----------------|------------|
| gate-review-round1-fixes | PASS | 3 | docs/C22StretchHighMeasured.md, docs/measure_c22_stretch_high.py | none |

Round 1 was the external pre-push gate (not run by this agent), VERDICT
REVISE, 2 MAJOR + 2 MINOR + 1 NIT. Round 2 (this agent's own Fletcher gate,
Explore subagent) re-verified every round-1 fix by re-running the harness
and caught one NEW CRITICAL the round-1 fix introduced (a hardcoded
conclusion string in `section_R` left unqualified after the frame that
breaks its universal claim was added). Round 3 confirmed that fix holds
(re-ran the harness bare and with `P D`, checked every printed number
against the doc) and PASSed with one NIT (a quoted fragment in §0a that
could drift from the harness's wording), which was fixed. A `pytest`
subset regression was caught and fixed along the way (this log's own
verbatim-quoted numbers tripped `test_no_other_document_retypes_the_split`;
fixed with the repo's existing `<!--stale-by-design-->` escape, same
precedent as `auto-2026-11-12-ts-c3-20`).

Final verification: `python -m pytest -q tests/test_readme_counts.py
tests/test_altport2_ports.py tests/test_wiring_accessors.py
tests/test_ml_companions.py tests/test_gate_e_ledger.py
tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
tests/test_ts_strike_20.py` → 1458 passed, 7 skipped.

No `pandas_ta/` module, test, or wiring file was touched — this is a
measured revert (PandasTa issue #135); the receipt is the only deliverable.

Task-file write-back: skipped — no local task-file convention detectable
in this worktree for this standalone fix-the-review-gate request (not a
`TODO.md`/board task).
