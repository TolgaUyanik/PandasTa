# Auto run g191-169 — 2026-11-10

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | G191-169 | issue #72 | Port GTJA191 alpha #169 (MACD of the smoothed lagged one-day change) as `g191_169`, Gates A-D, wiring, tests, `docs/G191169Measured.md`. Gate E and both repos' suites run by the launcher afterwards. |

## Clarifications (asked ONCE, before execution)
- None asked — `AskUserQuestion` is unavailable in this issue-solver session (system prompt
  override). One ambiguity arose and was resolved by the conservative/smaller-scope reading,
  logged as an ASSUMPTION in `01-G191-169.md`: whether the one-day lag in `C-C1` should be a
  tunable parameter (like `g191_152`'s `delay_length`) or hardcoded. Taken as hardcoded,
  matching the smaller-scope precedent already shipped in `g191_167`/`g191_151` (GTJA alphas
  whose names state a fixed "one-day change" rather than a tunable window), and matching the
  issue's own title ("lagged one-day change", not "lagged N-day change").

## Execution map
| Task | Lane | Why |
|------|------|-----|
| G191-169 | main thread | single task, no parallelism possible (one new module + its wiring across 4 touch points + its own test file + docs) |
