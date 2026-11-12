# Auto run — summary (TS-STRIKE-20, PandasTa issue #90)

Mode C, one task, 2026-11-12, branch `issue-90-ts-strike-20`.

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `ts-strike-20` | **done, with its last fix set unreviewed** — see below | 4 (the loop's cap): REVISE, PASS, REVISE, REVISE | 14, counted from `git status --short` (1 new module, 1 new test module, 1 new measure script, 1 new receipt, 7 wiring/doc edits, 3 run-folder files) | Gate E and both repos' suites are the launcher's; a later receipt session records the `docs/gate_e_ledger.csv` row and fills in Gate C's real-data counts |

**What "done, with its last fix set unreviewed" means.** The gate ran four
times, which is this session's cap (one round plus three re-runs). Every
finding of all four rounds was applied — round 4's six included, among them a
CRITICAL it found in round 3's own fix: pasting a reviewer's verdict verbatim
put slash-joined number runs into this folder and tripped
`tests/test_pine_coverage_csv.py::test_no_other_document_retypes_the_split`,
taking the suite to 4 failures while the receipt still claimed 3. Nothing is
left open, and each of round 4's fixes was verified by a run rather than by a
fifth reviewer (the guard by grep and by the suite, the suite counts by
re-running, the file count by `git status --short`). What no reviewer has seen
is that last fix set itself. Every verdict is quoted verbatim in
`01-ts-strike-20.md`, including the one editorial change made inside two of
the quotes and why.

Files:

* `pandas_ta/statistics/ts_strike_20.py` (new) — the indicator, `TS_STRIKE_20`
* `pandas_ta/statistics/__init__.py` — export
* `pandas_ta/__init__.py` — `Category["statistics"]`
* `pandas_ta/core.py` — `df.ta.ts_strike_20()`
* `tests/test_ts_strike_20.py` (new) — 144 tests
* `docs/measure_ts_strike_20.py` (new) — the run behind every number
* `docs/TsStrike20Measured.md` (new) — the receipt
* `README.md` — 322 → 323 in `Category`, 330 → 331 callable, statistics 31 → 32
* `docs/IndicatorDictionary.md` — regenerated; `TS_STRIKE_20` **ORD**, warm-up 20
* `docs/MLCompanionContract.md` — 667 → 668 tagged columns, 51 → 52 `ORD`
* `tests/test_altport2_ports.py` — `CATEGORY_TOTAL` 322 → 323
* `docs/reviews/auto-2026-11-12-ts-strike-20/{00-manifest,01-ts-strike-20,99-summary}.md`

## Suites run in this worktree

* `python -m pytest tests/test_ts_strike_20.py -q` → **144 passed**.
* `python -m pytest -q` → **3 failed, 5,954 passed, 83 skipped**, re-run after
  the last edit to any file in the tree (a prose-only edit broke it once — see
  `docs/TsStrike20Measured.md` §Gate F). The three failures:
  * `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
    — a `CLAUDE.md` *Known break*; needs the sibling `../AlternativeRepos`
    checkout and is deselected in CI.
  * `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` — the
    other *Known break*; the `supertrend` citation into the untracked
    `docs/pine/`.
  * `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` —
    reports `['mtd_ret', 'ts_strike_20']`: the row this port owes and one owed
    before this branch. Expected until the launcher's Gate E run and the
    receipt session; CI into `dev` skips it under `GATE_E_PENDING_OK=1`.

## Measurement runs

`python docs/measure_ts_strike_20.py` (whole script) plus each section
individually (`gate_a gate_b noise_floor gate_c_d meaning neighbours guards
cost`). Every number in `docs/TsStrike20Measured.md`, in the module docstring
and in the test module's docstring is printed by one of those runs or by
pytest, **except the cross-port figures borrowed from
`docs/TsC320Measured.md` and `docs/TsBinent20Measured.md` and the pooled
398,849-bar denominator in §Gate C**, each of which names the file it came
from on its own line.

## What is NOT measured here

* **Gate E.** Forbidden in this session (private engine, no `../Backtesting`
  access). The receipt carries *Gate E: pending, run by issue-solver after this
  session*.
* **Gate C on real data.** The 89 frozen ALTPORT-1 frames are not in this
  worktree; the pooled non-NaN / non-zero counts come from the launcher's Gate
  E run.
* **tsfresh's source.** Not installed, no web access. The attribution is to the
  feature name issue #90 gives; nothing in this port describes how tsfresh
  spells anything. This was round 1's MAJOR finding and the whole port was
  swept for it.
