# Auto run — LEAN-HURST-100 (issue #85)

**Date:** 2026-11-11
**Mode:** `/brutally-honest-review --auto` → Mode C (batch task execution; the
argument is a free-form task, not a plan file, so there is no Mode B pre-gate
and, per the skill, no Mode D refutation either — stated here once because the
invocation did not ask for one).
**Run folder:** `docs/reviews/auto-2026-11-11-lean-hurst-100/`

## Phase 1 — the resolved task

| id | scope | source |
|---|---|---|
| `lean-hurst-100` | Port the Hurst exponent in its lagged-difference form (QuantConnect Lean `HurstExponent(100, maxLag 20)`) through Gates A–D, wire it at all five touch points, write `tests/test_lean_hurst_100.py` and `docs/LeanHurst100Measured.md`. Gate E and both repos' suites are the launcher's. | the `--auto` argument, which restates PandasTa issue #85 (`docs/issues/084-lean-hurst-100.md`) |

One task, so there is no parallel lane and no ordering question: everything ran
on the main thread.

## Phase 2 — clarifications

`AskUserQuestion` is unavailable in this headless session, so no questions were
asked. The skill's rule applies: take the most conservative reading (the smaller
scope) and log it. **Assumptions, each the narrower choice:**

| # | question the issue leaves open | the conservative reading taken |
|---|---|---|
| A1 | Lean's `HurstExponent` C# source is not in this worktree and web access is unavailable. Port from what? | From the formula the issue **states**, and say so in the docstring and the receipt rather than implying a line-by-line reading of Lean. Gate A is pinned against a hand-derived closed-form window, the screen prototype, and an independent scalar loop. |
| A2 | `std`: population or sample? | `ddof=0` — numpy's default and the prototype's. The rejected `ddof=1` is measured, not dismissed (max \|diff\| 5.2e-4, Spearman 1.000000). |
| A3 | Which category? | `statistics`, with the other candidates (`cycles`, `volatility`) not taken: the column is a statistic of the path, and the two most recent statistics ports (`kpss`, `trend_scan`) are the precedent. One new module file, well inside the ≤ 3 cap. |
| A4 | Module and column name? | The screen's candidate id, `lean_hurst_100`, and `LEAN_HURST_{length}_{max_lag}` = `LEAN_HURST_100_20`. Precedent: `lot_zeroret_60`, `tf_centroid_20`, `osap_retskew_21` keep the candidate name with its window. |
| A5 | Expose `max_lag` as a parameter, or hardcode 20? | Expose it, defaulted to the issue's 20 and **clamped** to `length - 2`, with the effective value in the column name. A hidden constant would make the name a lie at any non-default `length`. |
| A6 | The ledger row for Gate E? | NOT written. The system prompt forbids running Gate E here; `docs/gate_e_ledger.csv` is untouched, the receipt says "pending, run by issue-solver after this session", and `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` is left failing on `['lean_hurst_100', 'mtd_ret']` as the rules require. |
| A7 | A rounding-noise floor the prototype does not have? | Added, because the unguarded form reports a plausible-looking slope out of pure float64 rounding on a geometric path (measured: 85 of 300 bars in [0.2723, 0.5359] on an exact ×1.5 ladder). Kept as the narrowest form that works: an **absolute** constant, so the module has one `.rolling(` call and therefore one causality surface, not two. |

## Phase 3 — execution map

| lane | why |
|---|---|
| main thread | a single task; the work needs the repo's protocol in context (five wiring touch points, counter files that several tests cross-check), and no two parts of it are independent enough to be worth a worktree |

## Phase 4/5 — gate and log

⚠ **No per-task review log or summary file was written in this run.** The
session ended after the port, its tests and `docs/LeanHurst100Measured.md` were
on disk but before the Phase 4/5 files (`01-lean-hurst-100.md`,
`99-summary.md`) were created, so this manifest is the whole run folder. Do not
read the absence of a REVISE log as a PASS: the Fletcher gate's outcome for
this task is **unrecorded**, and the evidence that stands on its own is the
measured file plus `tests/test_lean_hurst_100.py` (65 tests, all passing —
measured 2026-11-11 with `python -m pytest tests/test_lean_hurst_100.py -q`).
The reviewer the launcher runs next is the first recorded review of this port.
