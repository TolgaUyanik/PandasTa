# Run manifest — `/brutally-honest-review --auto` (Mode C), 2026-11-13

**Run folder:** `docs/reviews/auto-2026-11-13-ts-kurt-60/`
**Invocation:**
`/brutally-honest-review --auto "TS-KURT-60: port the indicator of issue #93
through Gates A-D, the wiring, the tests and docs/<Name>Measured.md, per the
issue and the rules in your system prompt (excess kurtosis of returns (60).
Source: tsfresh feature_calculators (MIT) — `kurtosis on 60 returns`.). Gate E
and the suites are run by the launcher afterwards."`

Mode C (batch task execution) — one free-form task, so one entry. Mode C has
no pre-gate; the task is a TODO-shaped reference, not a plan carrying
load-bearing reasoning.

## Phase 1 — the resolved task

| id | scope | source |
|---|---|---|
| `ts-kurt-60` | Port tsfresh's `kurtosis` of 60 returns as `pandas_ta/statistics/ts_kurt_60.py` through Gates A–D, with the five wiring touch points, a test module and `docs/TsKurt60Measured.md`. Gate E and both repositories' suites are the launcher's. | PandasTa issue #93 (TS-KURT-60), quoted verbatim in the issue-solver brief; local mirror `docs/issues/092-ts-kurt-60.md` (gitignored) |

## Phase 2 — clarifications

**None asked.** `AskUserQuestion` is unavailable in this headless session, so
every ambiguity was resolved by the most conservative reading (the smaller
scope) and logged as an ASSUMPTION below.

| # | ambiguity | conservative reading taken |
|---|---|---|
| A1 | "excess kurtosis" — Fisher's G2 (bias-corrected) or the biased g2? | The bias-corrected G2, because tsfresh's `kurtosis` is `pandas.Series.kurtosis` and the screen prototype is `rolling(60).kurt()`. Both alternatives are priced in `docs/TsKurt60Measured.md` §A5 rather than argued; for a fixed `length` the choice is an exact affine map, so a rank miner cannot see it. |
| A2 | 60 RETURNS or 60 CLOSES? | 60 returns (61 closes), the issue's words. The off-by-one is priced (Spearman 0.992198). |
| A3 | Simple or log returns? | Simple, the prototype's `ret`. Log returns priced (0.998596, max \|diff\| 0.2526). |
| A4 | A degenerate window — NaN, 0, or pandas' own answer? | NaN, the narrower claim: it emits nothing rather than a number a consumer cannot place. Both pandas answers measured (−3.0 from `rolling.kurt`, 0.0 from `Series.kurtosis`). |
| A5 | Re-derive the moments in numpy, or keep `rolling.kurt`? | Keep `rolling.kurt` — the smaller change, and the one that makes the port bit-equal to the screened prototype. Justified by measurement against an exact rational oracle (§A4), not by preference. |
| A6 | Gate E | NOT run here. The issue-solver rules reserve it for the launcher; the receipt says "pending, run by issue-solver after this session" and a test asserts the ledger carries no `TS_KURT` row yet. |

## Phase 3 — execution map

| task | lane | why |
|---|---|---|
| `ts-kurt-60` | main thread | One indicator, one scope, and every gate needs judgement about what the numbers mean. No parallel lane would have had anything to do that did not conflict. |

Reviewer lane: a fresh read-only `Explore` subagent per round (the "third
eye"), `--fletcher` on, dispatched after each implementation pass. Four rounds
maximum, per the session's standing review rule; the cap is 3 in the skill and
4 here, and the stricter instruction in the user's global rules wins.

## Phase 4/5 — where the log is

`01-ts-kurt-60.md` carries the implementation log, every reviewer verdict in
full, and what was changed in response. `99-summary.md` is the table.
