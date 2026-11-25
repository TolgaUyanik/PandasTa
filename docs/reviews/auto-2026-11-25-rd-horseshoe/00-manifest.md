# RD-HORSESHOE auto run — manifest

## Mode routing

Invocation: `/brutally-honest-review --auto "RD-HORSESHOE: port the indicator of issue
#164 through Gates A-D, the wiring, the tests and docs/<Name>Measured.md, ..."`.

The argument is a free-form task description (not a plan/spec file path, not a TODO tag
like `KB-6`) → **Mode C: Batch task execution**, single task, resolved as given per the
mode's own routing rule ("free-form list → take as given").

## Phase 1 — Select

| id | scope | source |
|---|---|---|
| RD-HORSESHOE | Port issue #164's `rd_horseshoe` (candles) through Gates A–D, wiring, tests, `docs/RdHorseshoeMeasured.md`. Gate E and whole-suite runs are out of scope (launcher's job per the task's own text). | issue #164 text + headless session system prompt |

Run folder: `docs/reviews/auto-2026-11-25-rd-horseshoe/`.

## Phase 2 — Clarify

No AskUserQuestion available in this headless session (system prompt: "take the most
conservative reading ... and log it as an ASSUMPTION"). One ambiguity resolved:

- **ASSUMPTION:** the issue's "cannot be above both" is read as the issue's own stated
  formula, `<= max(open1, close4)` for the bull case (mirrored `>= min(open1, close4)`
  for the bear's lows) — explicitly given in the issue text, not actually ambiguous, so
  this is a restatement rather than a judgment call. No other gap found: the issue names
  the source, the formula, the gates owed, and the done condition unambiguously.

No destructive or irreversible step was in scope (no push, no force-anything) — nothing
to pre-authorize.

## Phase 3 — Plan execution

| task | lane | why |
|---|---|---|
| RD-HORSESHOE | main thread | single task, no parallel counterpart; sequential dependency (module → wiring → tests → docs) and judgment calls (bar indexing, scale-free argument) throughout. |

## Phase 4/5 — see `01-rd-horseshoe.md` and `99-summary.md`.
