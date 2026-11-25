# Mode C manifest — RD-WICK-PRESSURE-10

## Tasks

1. `rd-wick-pressure-10` — port issue #170's `rd_wick_pressure_10` (candles) through
   Gates A-D, wiring, tests, `docs/RdWickPressure10Measured.md`. Gate E and whole suites
   are run by the launcher afterward.

## Clarifications (Phase 2)

None needed. The issue gives the formula directly
(`sum lower wick on bear candles - sum upper wick on bull candles`, scale-free form over
10 bars divided by the sum of ranges), the screen prototype
(`docs/issues/screen/ind_screen_r6.py`'s `rd_wick_pressure_10`) gives the exact arithmetic
to re-derive from the formula (not to cite as Gate A), and the launcher's own rules state
Gate E/F handling precisely. No destructive step anywhere in this task.

## Execution map

Single task, main thread (no parallel lane — one item, no scope conflict to isolate).

## Scope guardrails (from the launcher's system prompt, binding on this run)

- Never run Gate E (`gate_e_overlap.py`) or touch `../Backtesting`.
- Never run the whole suite — only this port's test module plus the named wiring/doc
  tests, plus the CPU-feature-disabled wrapper for this port's own module.
- At most 3 new `pandas_ta/<category>/*.py` files (this port adds exactly 1:
  `pandas_ta/candles/rd_wick_pressure_10.py`).
- `docs/<Name>Measured.md` records "Gate E: pending, run by issue-solver after this
  session" — not SHIP/STRUCK, since Gate E has not run yet.
