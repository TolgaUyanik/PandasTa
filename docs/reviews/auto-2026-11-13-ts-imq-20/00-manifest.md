# auto run — 2026-11-13 — ts-imq-20

`/brutally-honest-review --auto "TS-IMQ-20: port the indicator of issue #99
through Gates A-D, the wiring, the tests and docs/<Name>Measured.md, per the
issue and the rules in your system prompt (index mass quantile of |returns|
(20, q=0.5). Source: tsfresh feature_calculators (MIT) —
`index_mass_quantile(q=0.5) on 20 |returns|`.). Gate E and the suites are run
by the launcher afterwards."`

**Mode C** (batch task execution): the argument is a free-form task, not a
plan file, so there is no Mode B pre-gate. One task.

## Phase 1 — the task

| id | scope | source |
|---|---|---|
| `ts-imq-20` | Port tsfresh `index_mass_quantile(q=0.5)` over 20 \|returns\| as `pandas_ta/statistics/ts_imq_20.py`; Gates A–D; five wiring touch points; `tests/test_ts_imq_20.py`; `docs/TsImq20Measured.md`. Gate E and the two suites are the launcher's. | issue-solver, PandasTa #99 |

Run folder: `docs/reviews/auto-2026-11-13-ts-imq-20/`.

## Phase 2 — clarifications

`AskUserQuestion` is unavailable in a headless issue-solver session, so the
skill's rule applies: take the most conservative reading (the smaller scope)
and log it as an ASSUMPTION. None was escalated.

| # | the question the wording leaves open | reading taken | why it is the conservative one |
|---|---|---|---|
| A1 | Is `q` a parameter? | **No** — a module constant `Q = 0.5`. | The column name carries only `length`; a second parameter could not reach the name without changing it for every caller. Smaller API. q = 0.25 / 0.75 are priced in §A5 as different columns (rho ~0.59). |
| A2 | `length` counts returns or closes? | **Returns** (21 closes, first value at bar 20). | The issue says "on 20 \|returns\|". The alternative is priced: rho 0.906430, max \|d\| 0.1842. |
| A3 | Simple or log returns? | **Simple**, `close/close.shift(1) - 1` — the prototype's `ret`. | Matches the screen prototype bit for bit. Log is priced: rho 0.996198, one position of difference. |
| A4 | A dispersion floor, like the siblings `ts_medskew_20` / `ts_above_mean_20`? | **No floor.** | Adding one would REMOVE 280 honest windows on a ladder and 0 dishonest ones (Guards G3). The smaller change is not to add machinery the measurement does not justify. |
| A5 | What to do about the overlap with the shipped `TFCENTROID_20`? | **Ship with disclosure in five places**, do not revert. | Pooled +0.8466 / per-frame median 0.8545 / 0 of 9 frames ≥ 0.90 is DISCLOSE_GAP under `r3-perframe-0.90`, not STRUCK. Reverting on a band the rules do not strike would be the owner's call, not this session's; §E names exactly what would reverse it. |
| A6 | Real-data counts (Gate C) and Gate E? | **Owed, and labelled owed.** | `../Backtesting` is outside this worktree and the launcher runs Gate E. The receipt says "pending, run by issue-solver after this session" and `tests/test_ts_imq_20.py::test_the_gate_e_row_is_owed` asserts the ledger row is absent. |

## Phase 3 — execution map

| task | lane | why |
|---|---|---|
| `ts-imq-20` | **main thread** | One indicator, one category, five interlocking wiring points plus three documents whose counts must agree; nothing parallelisable without a barrier at every step. |

Gate: a fresh read-only Fletcher reviewer (`Explore` subagent) per round, never
the main thread. Four rounds ran; the log is `01-ts-imq-20.md`.

## Not run

* **Codex review.** The global rule asks for one BHR plus one `codex exec`
  review before a first push. `codex` is not an allowed command in this
  session (only `python`, `git`), so only the BHR loop ran. Recorded here
  rather than silently skipped.
* **Gate E.** The launcher's, by instruction.
* **Both repos' suites in clean worktrees.** The launcher's. The local full
  suite was run here: 3 failed, 7,495 passed, 85 skipped — the three being
  CLAUDE.md's known break, the `../AlternativeRepos`-only test CI deselects by
  name, and the owed Gate E row.
