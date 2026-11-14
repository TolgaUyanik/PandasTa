# auto run 2026-11-14 — `ts-energy-last-20`

`/brutally-honest-review --auto "TS-ENERGY-LAST-20: port the indicator of
issue #102 through Gates A–D, the wiring, the tests and
docs/<Name>Measured.md, per the issue and the rules in your system prompt
(share of 20-day squared returns in the last 5 bars. Source: tsfresh
feature_calculators (MIT) — `energy_ratio_by_chunks(num_segments=4,
segment_focus=3) on 20 returns`.). Gate E and the suites are run by the
launcher afterwards."`

**Mode C** (batch task execution): the argument is one free-form task
reference, not a plan file, so there is no step-0 pre-gate — Mode C
resolves task references, which carry no load-bearing plan reasoning.
Fletcher theatrics are ON. One task, so Phase 3's execution map is
trivial.

## Phase 1 — the task

| id | scope | source |
|---|---|---|
| `ts-energy-last-20` | Port tsfresh's `energy_ratio_by_chunks(num_segments=4, segment_focus=3)` over 20 simple returns as `pandas_ta/statistics/ts_energy_last_20.py`; Gates A–D; the five wiring touch points; `tests/test_ts_energy_last_20.py`; `docs/TsEnergyLast20Measured.md`. Gate E owed, run by the launcher. | the issue-solver task text for PandasTa issue #102, quoted verbatim in the session's system prompt |

Run folder: `docs/reviews/auto-2026-11-14-ts-energy-last-20/`.

## Phase 2 — clarifications

`AskUserQuestion` is unavailable in a headless issue-solver session and
the system prompt says to take the most conservative reading and log it.
No questions were asked. The readings taken, each the smaller-scope one:

| ASSUMPTION | the choice, and why it is the conservative one |
|---|---|
| A1 | **`SEGMENTS = 4` and `SEGMENT_FOCUS = 3` are module constants, not arguments.** `segment_focus` means "the last chunk" only because it is `num_segments - 1`; exposing either would let a caller change WHICH chunk the column reads under the same name. The precedent is `ts_peaks_20`'s `SUPPORT`. §A5.3/§A5.4 price the alternatives. |
| A2 | **Column name `TS_ENERGY_LAST_{length}_{SEGMENTS}`** = `TS_ENERGY_LAST_20_4`, following `TS_PEAKS_{length}_{SUPPORT}` and `TS_BINENT_{length}_{bins}`: length first, then the source's second parameter. |
| A3 | **`length` is the only argument, default 20, minimum 4.** Fewer returns than chunks leaves the focused chunk empty and `np.sum([])` is 0.0, so the column would be identically zero. |
| A4 | **Simple returns, not log returns.** The issue says "returns" and the prototype uses `c / c.shift(1) - 1`. §A5.1 prices the log reading (Spearman 0.999572). |
| A5 | **`length // 4` generalises the source rather than hard-coding the prototype's 5.** Checked against `np.array_split` itself for every length 4..240 (§A4). |
| A6 | **Gate E is not run here.** The system prompt forbids it and reserves it for the launcher; §E says "pending" and `test_the_gate_e_row_is_owed` asserts the ledger row is absent. |
| A7 | **No dispersion floor.** Two siblings have one; §G3 measures that adding it would empty 280 of 280 honest ladder windows and 0 dishonest ones. The smaller-scope reading is to add no guard that is not measured to buy something. |

## Phase 3 — execution map

| task | lane | why |
|---|---|---|
| `ts-energy-last-20` | main thread | one task, no parallel scope to split; the work needs main-context judgment (the gate protocol in `CLAUDE.md`), and every file it touches is on the issue's allow-list |

No subagent lanes. No worktree isolation.

## Phase 4/5

Per-task log and every review verdict verbatim: `01-ts-energy-last-20.md`.
Summary table: `99-summary.md`, whose round table is filled in as each
round returns and never before it.
