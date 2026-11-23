# Run manifest: TL-MSW-LEAD-20

**Mode:** C (batch, single task). **Run folder:** `docs/reviews/auto-2026-11-23-msw-lead-20/`.

## Task

- id: TL-MSW-LEAD-20
- scope: port issue #145 (MESA lead sine, fixed-period DFT form, length 20) through Gates A-D,
  the five wiring touch points, tests, and `docs/MswLeadMeasured.md`, per the issue text and the
  overriding session rules (Gate E and the whole suites run by the launcher afterwards; targeted
  test subset only).
- source: the task text given verbatim in the `/brutally-honest-review --auto` invocation.

## Clarify (Phase 2)

No gaps needing a user question. The issue text, the repo's `CLAUDE.md` porting protocol, and
the two precedent ports (`correlation_cycle`, `kalman_trend`/`pfe` test style) fully specify
scope, naming is a free implementation choice within convention (resolved below), and the
rules block in the system prompt overrides Gate E / whole-suite execution explicitly. No
AskUserQuestion round was needed.

**ASSUMPTION (conservative reading, logged per the headless rules):** the issue's catalog
candidate id is `tl_msw_lead_20`, but shipped indicator names in this repo do not carry a `tl_`
prefix (checked: no shipped Tulip-attributed indicator uses one, e.g. `decay` cites
`tulipindicators.org/decay` with no prefix). The module/function/column is named `msw_lead` /
`MSW_LEAD_<length>` — Tulip's own short name for this exact output — rather than inventing a
`tl_`-prefixed name that has no precedent elsewhere in `Category`.

## Execution map

Single task, sequential, main thread (judgment-heavy: formula re-derivation from a published
source, mutant design, gate bookkeeping across ~10 touch points). Not parallel-eligible.

## Phase 4 gate

One Fletcher review round against the full diff (new module, wiring, tests, measure scripts,
`MswLeadMeasured.md`, README/dictionary/contract/test-count edits). Report: `01-TL-MSW-LEAD-20.md`.
