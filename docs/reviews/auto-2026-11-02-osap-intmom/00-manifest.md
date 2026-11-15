# Manifest — OSAP-INTMOM (issue #40)

**Invocation:** `/brutally-honest-review --auto "OSAP-INTMOM: port the indicator of issue
#40 through Gates A-D, the wiring, the tests and docs/<Name>Measured.md, per the issue and
the rules in your system prompt (intermediate momentum, months t-12..t-7. Source: Open
Source Asset Pricing SignalDoc (Chen & Zimmermann; US monthly cross-section) — `IntMom
(Novy-Marx 2012), OSAP t 5.79`.). Gate E and the suites are run by the launcher
afterwards."`

**Mode:** C (free-form single task, hands-off, gated).

## Phase 1 — Select

One task: port `osap_intmom` (intermediate momentum, OSAP SignalDoc `IntMom`, Novy-Marx
2012) through Gates A-D, wiring, tests, and `docs/OsapIntmomMeasured.md`, per issue #40.
Run folder: `docs/reviews/auto-2026-11-02-osap-intmom/`.

## Phase 2 — Clarify

No AskUserQuestion available (headless issue-solver session). No ambiguity requiring a
question surfaced: the issue, the prototype (`docs/issues/screen/ind_screen.py:771-772`,
candidate `osap_intmom`), and the already-committed sibling port `osap_mrrev` #37 (whose
own docstring had already independently derived this exact 126/252 arithmetic as
corroboration) gave a fully determined scale-free formula and a precedent module shape.
One ASSUMPTION carried over, inherited from the issue itself and already disclosed by
`osap_mrrev`'s Gate A: the issue's own stated 21-trading-days/month conversion is taken as
given, not independently re-derived from the primary OSAP SignalDoc (unreachable in this
worktree). Category placement (momentum, matching `osap_mrrev`'s category and formula
shape) is a conservative reading, not a guess: identical formula family, identical
near/far-shift-ratio construction.

## Phase 3 — Plan execution

Single task, main thread (sequential, no parallel-eligible scope — one module plus its
five wiring touch points plus docs, all interdependent).

| Task | Lane | Why |
|---|---|---|
| osap_intmom port | main thread | Five wiring touch points + README/MLCompanionContract/dictionary edits all interdependent; no independent scope to parallelize |

## Phase 4 — Execute + gate

See `01-osap-intmom.md`.

## Phase 5 — Report

See `99-summary.md`.
