# auto-run manifest — 2026-09-07 — runid `fvg-sqz-pinebi`

Invocation: `/brutally-honest-review --auto FVGDEAD-0 FVGDEAD-1 SQZOFF-0 PINEBI-0 PINEBI-1a PINEBI-1b PINEBI-1c PINEBI-1d PINEBI-1e PINEBI-2`
Mode: C (batch task execution). Fletcher gate ON, 3-round cap per task group.
Task source: `PandasTa/TODO.md`.

## Resolved tasks

| id | scope | outcome |
|---|---|---|
| FVGDEAD-0 | fire-or-delete `fvg`'s zone columns, on Gates C/D/E | repaired, PASS |
| FVGDEAD-1 | find every `IN_FVG_*` reference; name suspect mined rules | done, PASS |
| SQZOFF-0 | NaN-safe cast in `squeeze`/`squeeze_pro` | done, PASS |
| PINEBI-0 | freeze the Pine coverage audit into a CSV | done, ESCALATED at cap |
| PINEBI-1a | add the rolling primitives | done (18), ESCALATED at cap |
| PINEBI-1b…-1e, -2 | port batches | **not started — deferred by the user** |

## Clarifications (Phase 2, one batched round)

1. **Sequencing.** Ten tasks = 3 defects + 46 indicators, each needing Gates A–F and a 3-round gate.
   → **"Defects + PINEBI-0 + 1a"**. The remaining five PINEBI sub-tasks stay open.
2. **Who decides fire-or-delete on `fvg`?** → **"Repair if it clears the gates"**; my call on the
   measurement.
3. **Gate E sample.** → **"Match existing precedent"** — the Grid A universe and method of
   `measure_ifvg_overlap_full.py` (89 BIST_100 frames, 408,253 daily bars, all 361 engine columns).
4. **Pine fidelity for the primitives.** → **"Pine-exact, lag documented"** — match Pine bar-for-bar
   including `pivothigh`'s confirmation lag, and document that lag as the causality cost.

## Assumptions (logged, not asked)

- A1 — "Match existing precedent" means the same universe AND the same script shape, so the FVG
  measurement was written from `measure_ifvg_overlap_full.py` rather than invented.
- A2 — Repairing an engine copy of an indicator is in scope where it is research code; the TRADING
  FREEZE reaches `deploy/` only. (Round 1 of the gate corrected an earlier, wider reading.)
- A3 — A primitive is not an indicator: `_pine.py` functions stay out of `Category` and off `df.ta`,
  so `df.ta.strategy()` can never sweep them into a feature set.
- A4 — Where a Pine name would shadow a Python builtin, the port is renamed and the divergence
  documented (`alltime_max`/`alltime_min`).

## Execution map

| task | lane | why |
|---|---|---|
| all | main thread | Shared files (`TODO.md`, the fork's test suite, the coverage CSV) and sequential dependencies: FVGDEAD-1 reads what FVGDEAD-0 changed, PINEBI-1a is scoped from PINEBI-0's output. No lane was independent enough to isolate. |

Gates ran as two groups rather than one per task — the three defects share a suite and a review
surface, and PINEBI-0/-1a are a single artifact-plus-implementation pair. Each group took its own
three rounds.
