# Manifest — auto-2026-11-21-c22-embedding-dist

## Phase 1 — Select

One task, resolved from the invocation's free-form task text (not a TODO
tag, not a plan file):

| id | scope | source |
|---|---|---|
| port-132 | Port PandasTa issue #132 (C22-EMBEDDING-DIST) through Gates A-D, wiring, tests and `docs/<Name>Measured.md`, per the issue and the session's system-prompt rules. Gate E and whole suites are the launcher's job. | invocation argument, verbatim |

Run folder: `docs/reviews/auto-2026-11-21-c22-embedding-dist/`

## Phase 2 — Clarify

No gaps found. The issue text, the session's system-prompt rules (file
scope, allowed commands, Gate E/F deferral, commit-message format, ending
tokens) and `CLAUDE.md`'s catch22 port protocol together fully specify goal,
scope and the "measured revert" done-criterion. No question needed asking.
ASSUMPTIONS: none beyond what the system prompt already states.

## Phase 3 — Plan execution

| task | lane | why |
|---|---|---|
| port-132 | main thread | single task, no parallel counterpart, needs main-context judgment (Gate A correctness calibration, read of multiple existing catch22 port receipts for house convention) |

## Outcome

Gate A (correctness) could not be established on every frame: black-box
calibration against `pycatch22` 1.0.2 (oracle only, never read as source,
never shipped) across 34 structural variants of the public definition (30
histogram-parameter readings + 4 alternative structures), plus a 21-point
fine bin sweep, a 25-frame generalisation cross-check, and a data-driven
bin-count family (round 4, below): the closest reading, numpy's own
`bins='auto'` convention, reproduces the oracle to float precision on 30
of 33 frames, but 3 stay off by exactly one bin — short of this fork's own
Gate A bar (`c22_acf_first_min`'s "0 of N disagree"). **Measured revert**:
no `pandas_ta` module, test or wiring was added. Receipt:
`docs/C22EmbeddingDistMeasured.md` and `docs/measure_c22_embedding_dist.py`,
both committed.
