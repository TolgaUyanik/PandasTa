# Auto run auto-2026-11-27-rd-adx8-med20-prepush-r1 — 2026-11-27

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | PREPUSH-R1 | pre-push review gate, round 1 of 3, HEAD ebc180eb00ea | Fix the one MAJOR (Gate C row still says "owed with Gate E" even though the launcher's Gate E run already gives the real-data counts) and the three MINOR findings (stale "Gate E: pending" clause in `tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` comment; a `PLACEHOLDER` comment left on a measured, pinned `CATEGORY_BUCKETS` line; a "fourth decimal" precision claim that is actually agreement to three decimals). Fix the NIT (a dead branch in `rd_adx8_med20.py`'s `min_bars` guard) only if cheap and safe.

## Clarifications (asked ONCE, before execution)
- `AskUserQuestion` is unavailable in this headless session. No questions asked. One judgment
  call: the NIT fix (simplify `min_bars = 2 * adx_length + max(length, min_periods)` to
  `2 * adx_length + length`) changes `rd_adx8_med20.py`'s source bytes, which changes its sha1 --
  and the Gate E run already recorded in `docs/gate_e_ledger.csv` is pinned to the CURRENT sha1
  (`f699c01cd00608423ff369bc3924d3b3fae32aaf`). Applying the NIT would make
  `tests/test_gate_e_ledger.py::test_row_still_describes_its_module` fail (confirmed by actually
  making the edit, running the suite, seeing the failure, then reverting). Not "cheap and safe"
  by the invocation's own bar, so left alone. Logged as an ASSUMPTION, most conservative reading
  (never invalidate an already-recorded measurement for a cosmetic win).

## Execution map
| Task | Lane | Why |
|------|------|-----|
| PREPUSH-R1 | main thread | all findings touch the same doc/test pair for one indicator; no independent scope to split across subagents |
