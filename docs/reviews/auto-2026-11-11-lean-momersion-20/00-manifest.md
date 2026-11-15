# Auto run — LEAN-MOMERSION-20 (issue #86)

**Date:** 2026-11-11
**Mode:** `/brutally-honest-review --auto` → Mode C (batch task execution; the
argument is a free-form task, not a plan file, so there is no Mode B pre-gate
and, per the skill, no Mode D refutation either — stated here once because the
invocation did not ask for one).
**Run folder:** `docs/reviews/auto-2026-11-11-lean-momersion-20/`

## Phase 1 — the resolved task

| id | scope | source |
|---|---|---|
| `lean-momersion-20` | Port Gilles' Momersion index (QuantConnect Lean `MomersionIndicator(20)`, `100*MC/(MC+MRC)` over same/opposite-sign consecutive return pairs) through Gates A–D, wire it at all five touch points, write `tests/test_lean_momersion_20.py` and `docs/LeanMomersion20Measured.md`. Gate E and both repos' suites are the launcher's. | the `--auto` argument, which restates PandasTa issue #86 (`docs/issues/085-lean-momersion-20.md`) |

One task, so there is no parallel lane and no ordering question: everything ran
on the main thread.

## Phase 2 — clarifications

`AskUserQuestion` is unavailable in this headless session, so no questions were
asked. The skill's rule applies: take the most conservative reading (the
smaller scope) and log it. **Assumptions, each the narrower choice:**

| # | question the issue leaves open | the conservative reading taken |
|---|---|---|
| A1 | Lean's `MomersionIndicator` C# source is not in this worktree and web access is unavailable. Port from what? | From the formula the issue **states**, and say so in the docstring and the receipt rather than implying a line-by-line reading of Lean. Gate A is pinned against three hand-derived windows with integer answers, the screen prototype (retyped AND imported from `docs/issues/screen/ind_screen.py`), and an independent per-window scalar loop. |
| A2 | Which side does a ZERO return fall on? | Neither, as "same/opposite-sign" says, and as the prototype does. The `if (p > 0) MC++ else MRC++` reading — flat → mean reversion, which a straight C# transcription would produce — is measured rather than dismissed: bit-equal on a continuous walk, max \|diff\| 55.7143 and Spearman 0.8399 on a 0.5 price grid. This is the decision that matters most on real (gridded) quotes. |
| A3 | Does the window hold `length` PAIRS or `length` RETURNS? | PAIRS (the prototype's reading, and the one the Gate E screen measured), so the column reads `length + 2` closes and warms up in 21 bars. The returns reading is priced: max \|diff\| 4.4737, Spearman 0.9685, and it fires one bar earlier. |
| A4 | What does the column do before its window fills, and when a window has no signed pair at all? | NaN in both cases — never the neutral 50 that some implementations emit, because a constant head is data to this fork's ML contract, and a window of nothing but flat bars has no share to report. Measured: 21 warm-up bars; an exactly flat frame and a staircase with non-adjacent steps both fire 0/300. |
| A5 | Which category? | `momentum`. The nearest shipped column by construction is `psl` (the share of up bars), which lives there; the measured \|ρ\| against it on a synthetic walk is 0.0197, so it is a relative and not a restatement. One new module file, well inside the ≤ 3 cap. |
| A6 | Module and column name? | The screen's candidate id, `lean_momersion_20`, and `LEAN_MOMERSION_{length}` = `LEAN_MOMERSION_20`. Precedent: `lean_hurst_100`, `lot_zeroret_60`, `tf_centroid_20` keep the candidate name with its window and parameterise the column. |
| A7 | Expose `length`, or hardcode the issue's 20? | Expose it, defaulted to 20, with a floor of 2 — a one-pair window can only read 0 or 100, which is a flag and not a share. The floor and the `int()` truncation rule are measured in the guard table. |
| A8 | The ledger row for Gate E? | NOT written. The system prompt forbids running Gate E here; `docs/gate_e_ledger.csv` is untouched, the receipt's Gate E section says it is pending and run by issue-solver, and `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` is left failing on `['lean_momersion_20', 'mtd_ret']` as the rules require. |
| A9 | Gate B on a DISCRETE, sign-driven column, where the usual path sweep catches a one-bar-ahead mutant only about half the time? | Keep the path sweep AND add a directed probe rather than report the weak number alone: for each J, multiply the tail by 0.5 or 2.0 — whichever changes the sign of `r[J]` — which is exact and changes exactly one return. Both probes' numbers are reported, including the frames where the directed one still misses. |

## Phase 3 — execution map

| lane | why |
|---|---|
| main thread | a single task; the work needs the repo's protocol in context (five wiring touch points, counter files that several tests cross-check), and no two parts of it are independent enough to be worth a worktree |

## Phase 4/5

The per-task log, with all four review rounds quoted verbatim, is
`01-lean-momersion-20.md`. The run summary is `99-summary.md`.
