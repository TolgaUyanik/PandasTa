# `/brutally-honest-review --auto` run — TS-AC1-60 (PandasTa issue #94)

Mode C (batch task execution), one task, run on 2026-11-13 in worktree
`PandasTa-94-ts-ac1-60`, branch `issue-94-ts-ac1-60`.

## Phase 1 — the task

| id | scope | source |
|---|---|---|
| `ts-ac1-60` | Port tsfresh's `autocorrelation(x, lag=1)` of 60 returns as `pandas_ta/statistics/ts_ac1_60.py` through Gates A–D, with the five wiring touch points, a test module, `docs/measure_ts_ac1_60.py` and `docs/TsAc160Measured.md`. Gate E and both repositories' suites are the launcher's. | PandasTa issue #94 (TS-AC1-60), quoted verbatim in the issue-solver brief; local mirror `docs/issues/093-ts-ac1-60.md` (gitignored) |

Run folder: `docs/reviews/auto-2026-11-13-ts-ac1-60/`.

## Phase 2 — clarifications

`AskUserQuestion` is unavailable in this headless session, so every open
reading was decided by the most conservative (smallest-scope) reading and is
logged here as an ASSUMPTION. Each one is also measured and priced in
`docs/TsAc160Measured.md` rather than merely asserted.

| # | open reading | decision (conservative) | where it is priced |
|---|---|---|---|
| A1 | The issue names the tsfresh formula as the source and the screen prototype `corr(r, delay(r,1), 60)` as the prototype. They are **not** the same statistic: tsfresh demeans by the window's single mean, normalises by the population variance and divides by `n - lag`; the prototype is a Pearson correlation of two 60-pair slices over 61 returns. | Ship the **tsfresh formula**, because the issue's "Gates owed" says Gate A starts from the source formula and not the prototype. The prototype is measured as a variant and the screen's Gate E numbers are flagged as belonging to it, not to this column. | `docs/TsAc160Measured.md` §A2, §A6 |
| A2 | `autocorrelation` takes a `lag`; the issue fixes `lag=1` and the indicator's name says `AC1`. | Do **not** expose a `lag` parameter. `length` is the only parameter; a `lag` keyword would let a caller produce a column named `TS_AC1_*` that is not a lag-1 autocorrelation. | module docstring (Args), `docs/TsAc160Measured.md` §Guards |
| A3 | tsfresh returns NaN when `np.isclose(var, 0)`, i.e. when the window's return variance is below `1e-8` — an absolute threshold that empties a window whose return sd is under 1e-4. | Reject that threshold and use this fork's existing habit: a floor of `(4096 eps)²` on the population variance, i.e. `sd > 9.09e-13`, the same comparison `statistics/ts_c3_20.py` makes. Both are measured, including how many bars each empties. | `docs/TsAc160Measured.md` §A5, §Guards |
| A4 | `length` is 60 **returns** (61 closes) or 60 closes (59 returns). | 60 returns, which is what the issue's line says (`on 60 returns`) and what the prototype reads. | `docs/TsAc160Measured.md` §A6 |
| A5 | Gate E. | NOT run here. The issue-solver rules reserve it for the launcher; the receipt says "pending, run by issue-solver after this session" and a test asserts the ledger carries no `TS_AC1` row yet. | `docs/TsAc160Measured.md` §Gate E |

## Phase 3 — execution map

| task | lane | why |
|---|---|---|
| `ts-ac1-60` | main thread | One indicator module plus five wiring touch points in shared files (`pandas_ta/__init__.py`, `core.py`, `README.md`, `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py`). Nothing to parallelise: a single file scope with ordering dependencies (module → wiring → dictionary regeneration → counts). |

Gate: a fresh `/brutally-honest-review` Fletcher reviewer subagent per round,
read-only, against the committed-to-be files. Round cap 4 (session rule:
round 1 plus three re-runs). Verdicts are quoted in full in
`01-ts-ac1-60.md`.
