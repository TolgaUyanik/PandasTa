# auto-run manifest — TS-CID-CE-20 (issue #95)

Invocation: `/brutally-honest-review --auto "TS-CID-CE-20: port the indicator
of issue #95 through Gates A-D, the wiring, the tests and
docs/<Name>Measured.md, per the issue and the rules in your system prompt
(complexity estimate CID-CE of returns (20). Source: tsfresh
feature_calculators (MIT) — cid_ce(x, normalize=True) on 20 returns). Gate E
and the suites are run by the launcher afterwards."`

Mode: **C** (batch task execution). The argument is a free-form task, not a
plan file, so there is no step-0 pre-gate — Mode C resolves tasks, which do
not carry load-bearing reasoning the way a plan does. `--refute` was not
passed.

## Phase 1 — the task

| id | scope | source |
|---|---|---|
| ts-cid-ce-20 | port tsfresh `cid_ce(x, normalize=True)` on 20 returns as `pandas_ta/statistics/ts_cid_ce_20.py`, through Gates A–D, five wiring points, tests and `docs/TsCidCe20Measured.md` | the headless issue-solver prompt for GitHub issue #95, plus the owner's local tracker copy, which is **`docs/issues/094-ts-cid-ce-20.md`** — the tracker's own numbering is offset from GitHub's, and that file's first line reads "094 TS-CID-CE-20 … On GitHub: #95" (gitignored, so a clone does not have it) |

Run folder: `docs/reviews/auto-2026-11-13-ts-cid-ce-20/`.

## Phase 2 — clarifications

`AskUserQuestion` is unavailable in a headless run, so every ambiguity was
resolved by the most conservative (smallest-scope) reading and logged here.

| # | ambiguity | conservative reading taken |
|---|---|---|
| A1 | Gate E | NOT run here. The system prompt forbids touching `../Backtesting`; `docs/TsCidCe20Measured.md` says "Gate E: pending, run by issue-solver after this session" and the ledger row is left absent, so `tests/test_gate_e_ledger.py` reports it owed. |
| A2 | which formula ships — the issue's source line or the screen prototype | the SOURCE line, per the issue's own "Gates owed" ("Gate A starts from the source formula, not the prototype"). Here the two differ only by `ddof`, which is measured and priced rather than assumed (A6/A7 of the measured doc). |
| A3 | the `s == 0` branch of tsfresh (`return 0.0`) | NOT copied. 0.0 is below the column's reachable minimum of 0.701759, so it would fabricate an impossible value; this port returns NaN, and the difference is measured on a flat frame (280 windows). |
| A4 | simple or log returns | SIMPLE, the prototype's `ret`. Log returns priced: Spearman 0.999909, max difference 4.8e-02. |
| A5 | 20 returns or 20 closes | 20 RETURNS, so 21 closes, first value at bar 20. The 19-return reading priced: Spearman 0.949216, max difference 1.4179. |
| A6 | `length` floor | 3. A two-return window is identically 2.0 (measured on 38 windows), so it cannot vary; anything below 3 falls back to the default 20 rather than shipping a constant. |
| A7 | guards beyond the source | kept to the three this fork already uses on return-based statistics (`ts_ac1_60`, `ts_c3_20`): a 4096-eps variance floor, a per-return square bound, an accumulator trust test. Each is priced in both directions — what it costs on clean frames and what it catches — and the one that catches nothing on the shapes tested would have been removed; the trust test earns its place on a volatile-then-frozen frame (181 bars, error 6.323 against a per-window oracle whose median there is 5.757). |
| A8 | whether to fix the pre-existing `Category` mutation defect found while running the suite | NOT fixed, and NOT this issue's. `pandas_ta/core.py:453` returns the live `Category[name]` list object and `core.py:692` then calls `ta.remove(x)` on it, so any category-mode `df.ta.strategy(...)` deletes the excluded names from the module-level `Category` for the rest of the process. Measured in this worktree: `python -m pytest tests/test_wiring_accessors.py tests/test_altport2_ports.py -q -p no:randomly` fails with "Category total 325, expected 328" while `tests/test_altport2_ports.py` alone passes. It is order-dependent and pre-existing (the arithmetic is −3 either way, so `dev` behaves the same), and fixing it would change `core.py` behaviour on no evidence from this issue. Written up in `01-ts-cid-ce-20.md`. |

## Phase 3 — execution map

| lane | why |
|---|---|
| main thread | one task, one indicator, needs the measurement loop (write module → measure → write the numbers back) in one context. No subagent lane, no worktree isolation. |

Gate: one Fletcher reviewer subagent per round against the task's output,
`--fletcher` on, read-only, cap 3 REVISE rounds. Verdicts quoted verbatim in
`01-ts-cid-ce-20.md`.
