# Run manifest — `/brutally-honest-review --auto`, 2026-11-13, `ts-aggac-60`

Mode C (batch task execution), one task. `--fletcher` theatrics on by
default. No pre-gate: Mode C resolves task references, not a plan carrying
load-bearing reasoning.

## The task, as given

> TS-AGGAC-60: port the indicator of issue #96 through Gates A-D, the wiring,
> the tests and docs/<Name>Measured.md, per the issue and the rules in your
> system prompt (mean return autocorrelation, lags 1-10 (60). Source: tsfresh
> feature_calculators (MIT) — `agg_autocorrelation(f_agg='mean', maxlag=10)
> on 60 returns`.). Gate E and the suites are run by the launcher afterwards.

Source issue: PandasTa #96, migrated from the owner's local tracker
(`docs/issues/095-ts-aggac-60.md`; `docs/issues/` is gitignored, so it exists
only on the owner's machine and nothing under it is committed).

## Phase 2 — clarifications

`AskUserQuestion` is unavailable in a headless issue-solver session, so every
open reading was taken at its most conservative (smallest-scope) value and
logged as an ASSUMPTION rather than asked. None of them blocked work.

| # | Question the task left open | Reading taken | Why, and where it is priced |
|---|---|---|---|
| A1 | Which formula: the issue's source line, or the screen prototype? | The SOURCE formula. | The issue's own *Gates owed* says "Gate A starts from the source formula, not the prototype". The prototype is retyped, measured against, and the gap disclosed: Spearman 0.902932, max \|difference\| 4.7e-02, first bar 70 against 60. `docs/TsAggac60Measured.md` A7. |
| A2 | `agg_autocorrelation` goes through `statsmodels.acf(adjusted=True)`; `autocorrelation` spells the quotient directly. Same number? | Treated as a claim to MEASURE, not to assume. | Measured: 3.469e-17 over 200 random windows, and the retyped adjusted `acf` is bit-exact against the installed statsmodels. A2. |
| A3 | Is `maxlag` a parameter, as `ts_c3_20`'s `lag` is, or fixed, as `ts_ac1_60`'s is? | A PARAMETER, with the column named `TS_AGGAC_{length}_{maxlag}`. | `ts_ac1_60` fixes `lag` because the name `AC1` already carries it; `TS_AGGAC` does not, so a fixed 10 would ship a column whose name hides a parameter. Naming-is-API is the deciding rule, and the clamp puts the EFFECTIVE value in the name. |
| A4 | What is the minimum `length`? | `MIN_LENGTH = 3`, with `maxlag` clamped to `length - 2`. | Smaller scope than inventing a new floor: 3 is `ts_ac1_60`'s, and the clamp is `ts_c3_20`'s habit. At `length` 3 the clamp gives `maxlag` 1, which IS `ts_ac1_60`'s statistic — a free cross-check. |
| A5 | Degenerate window: tsfresh's `var < 1e-10` branch returns the mean of zeros, i.e. 0.0. Follow it? | NO — report NaN. | 0.0 is an ordinary reading of this column (25.50% of iid windows are above it), so the fabrication would be invisible. Both tsfresh guards are retyped and measured beside this module's floor. A5. |
| A6 | Gate E? | NOT run, per the session rules. | `docs/gate_e_ledger.csv` carries no row; `TsAggac60Measured.md` says "Gate E: pending, run by issue-solver after this session"; a test asserts the row is absent so the receipt session is forced back here. |

## Phase 3 — execution map

One task, main thread. No parallel subagent lanes: the whole port is one
module plus its wiring, tests and receipt, and every file touches the same
scope. Fletcher reviewers ran as fresh read-only `Explore` subagents, which
is the point of the third eye — the main thread wrote the code and cannot
review it honestly.

| step | lane | artefact |
|---|---|---|
| read the issue, the screen prototype, the two merged sibling ports (`ts_ac1_60` #94, `ts_cid_ce_20` #95) | main | — |
| derive the port and write it | main | `pandas_ta/statistics/ts_aggac_60.py` |
| write the measurement script and run every section | main | `docs/measure_ts_aggac_60.py` |
| wire the five touch points plus README / dictionary / contract / `CATEGORY_TOTAL` | main | 7 files |
| write the test module | main | `tests/test_ts_aggac_60.py` |
| write the receipt | main | `docs/TsAggac60Measured.md` |
| review rounds 1–4 | fresh `Explore` subagent each | `01-ts-aggac-60.md` |

## Destructive steps

None. Nothing was deleted, force-pushed, deployed or published. The session
never reads or writes outside this worktree, and never runs Gate E.
