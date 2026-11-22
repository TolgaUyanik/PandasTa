# Auto run auto-2026-11-22-b3-qtd-ret — 2026-11-22

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | B3-QTD-RET | Issue #205 | Port quarter-to-date return (`qtd_ret`) through Gates A-D, wiring, tests, `docs/QtdRetMeasured.md`. Gate E and whole suites run by the launcher after this session. |

## Clarifications (asked ONCE, before execution)
- `AskUserQuestion` is unavailable in this headless session (system prompt). No questions asked;
  ambiguities are logged as ASSUMPTIONS in `01-B3-QTD-RET.md` with the smaller-scope reading taken.

## Execution map
| Task | Lane | Why |
|------|------|-----|
| B3-QTD-RET | main thread | single task, needs judgment against CLAUDE.md's gate table and the sibling `mtd_ret` precedent; no parallel scope to split |
