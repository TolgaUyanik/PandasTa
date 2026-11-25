# Summary — C22-RS-RANGE pre-push gate fix round

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| 01-c22-rs-range-gate-fix | PASS | 2 | `docs/measure_c22_rs_range.py`, `docs/C22RsRangeMeasured.md` | none |

All 3 MAJOR findings from the quoted pre-push gate fixed and verified by
direct re-execution of the harness (oracle gated behind `find_spec`, the
unmeasured isolation claim removed, the SEARCH grid widened from 10 to 20
structural hypotheses with the ceiling re-measured at an unchanged ρ=0.364).
Both MINOR findings (ddof mismatch, position-broken Spearman) and all four
NIT text issues fixed. This fix round's own gate (not the quoted pre-push
one) needed one internal REVISE round: the first pass at updating §A3's
table picked the wrong `min_side` for two of the sixteen rows (both
"connected" rows for the newly-added DFA-family variants); corrected to
match the harness's own printed output, then PASSed clean.

No module, wiring touch point, or test file was added — the issue stays a
measured revert, receipt kept as required.
