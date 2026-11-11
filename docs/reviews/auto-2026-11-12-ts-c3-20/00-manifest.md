# Auto run — TS-C3-20 (`/brutally-honest-review --auto`), 2026-11-12

Mode C (batch task execution), one task. Branch `issue-88-ts-c3-20`.

## Phase 1 — the resolved task

| id | scope | source |
|---|---|---|
| `ts-c3-20` | Port the indicator of PandasTa issue #88 through Gates A–D, the five wiring touch points, the tests and `docs/TsC320Measured.md`. Gate E and both repos' suites are run by the launcher afterwards. | the `--auto` argument, which quotes issue #88: *C3 nonlinearity of returns (20). Source: tsfresh feature_calculators (MIT) — `c3(x, lag=1) = mean(x[t]*x[t-1]*x[t-2]) on 20 returns`* |

Run folder: `docs/reviews/auto-2026-11-12-ts-c3-20/`.

## Phase 2 — clarifications

**None asked.** `AskUserQuestion` is unavailable in this headless session, so
every open reading was decided by the most conservative (smallest-scope)
option and logged here as an ASSUMPTION. Each one is also priced against the
alternative in `docs/TsC320Measured.md` §Gate A, so a reader can see what the
choice cost rather than taking it on trust.

| # | ASSUMPTION | why this reading | what the alternative costs (measured) |
|---|---|---|---|
| A1 | Category is **statistics** | a standardised third moment of returns is a window statistic, and the fork's two closest neighbours (`lean_hurst_100`, `osap_retskew_21`) sit there | none measured; a category move changes no values, only `Category`/`core.py` placement |
| A2 | `lag` is a **parameter**, default 1, and the column name encodes it (`TS_C3_20_1`) | tsfresh's own signature is `c3(x, lag)`; Gate A starts from the source formula, and "Naming is API" wants both parameters in the name | hard-coding `lag=1` would name the column `TS_C3_20` and lose the source's parameter |
| A3 | the divisor is the **sample** sd (`ddof=1`) | the prototype's `std(r,20)`, which is pandas' default; the divisor is the prototype's own addition, so the prototype IS the source for it | `ddof=0` is a strict rescaling by 1.079977: max \|diff\| 0.0616, Spearman 1.000000 |
| A4 | the numerator averages **only the 18 triples inside the window** | the smaller reach: the column then reads exactly `length + 1` closes | a full 20-wide mean reaches 2 bars further back: max \|diff\| 0.9937, Spearman 0.9201, first fire at bar 22 not 20 |
| A5 | a window whose returns vary only at **rounding level** is NaN, floored at 4096 eps | the fork's existing habit (`lean_hurst_100`, `range_compress_run`); the prototype's `sdiv` only strips infinities | unguarded, a 1%-a-bar ladder fires 280 of 300 bars with values up to 7.96e+41 |
| A6 | **Gate E is not run here**, and no ledger row is added | the session rules forbid reading `../Backtesting`; `docs/TsC320Measured.md` says "pending, run by issue-solver after this session" | `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` fails, reporting `['mtd_ret', 'ts_c3_20']` — expected, and skipped in CI into `dev` |
| A7 | **Gate C's real-data counts are left owed** | they come out of the launcher's Gate E run; this worktree has no BIST frames | the synthetic distribution is measured instead, and the doc says which rows are synthetic |

## Phase 3 — execution map

| task | lane | why |
|---|---|---|
| `ts-c3-20` | main thread | one task, and it needs main-context judgment (the gate protocol, the measured-claims discipline, the five wiring touch points across files another agent must not edit in parallel) |

Gate: one Fletcher reviewer subagent (read-only `Explore`) per round, up to 4
rounds (the session's review-loop rule), verdicts quoted verbatim in
`01-ts-c3-20.md`.
