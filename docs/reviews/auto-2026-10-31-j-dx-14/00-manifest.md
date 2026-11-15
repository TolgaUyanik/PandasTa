# Mode C manifest -- DX port (issue #120 / J-DX-14)

## Task

Single free-form task, as given in the invocation:

> J-DX-14: port the indicator of issue #120 through Gates A-D, the wiring,
> the tests and docs/<Name>Measured.md, per the issue and the rules in your
> system prompt (directional movement index DX, unsmoothed (14). Source:
> jesse (MIT) -- `dx.py: 100*|DI+ - DI-|/(DI+ + DI-)`.). Gate E and the
> suites are run by the launcher afterwards.

Source: `docs/issues/screen/ind_screen_r2.py:38-51,101-102` (helpers
`dm_wilder`/`dx_wilder`, candidate `j_dx_14`), issue #120 body (verbatim in
the system prompt).

## Clarifications (Phase 2)

None asked. `AskUserQuestion` is unavailable in this headless issue-solver
session; the issue text and this repo's `CLAUDE.md` porting protocol fully
specify scope, gates and done-when criteria, so no ambiguity needed
resolving. One ASSUMPTION made, conservative reading:

- **ASSUMPTION:** DX is built on this fork's own already-shipped `adx()`
  (Wilder RMA, scalar 100) rather than re-deriving +DI/-DI from the
  prototype's `dm_wilder`/`dx_wilder` helpers. Smaller blast radius (no new
  DI/DM math to get wrong; `adx()`'s own correctness is already upstream and
  out of scope), it is a direct, literal application of the source formula
  `100*|DI+ - DI-|/(DI+ + DI-)` to `adx()`'s own `DMP_<length>`/`DMN_<length>`
  terms, and it mirrors the precedent this fork already set for `adxr()`
  (same reuse strategy, closed port, `docs/AdxrMeasured.md`).

## Execution map (Phase 3)

Single task, non-parallelizable (it touches the shared wiring files
`pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_altport2_ports.py`,
`README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md` --
all five wiring touch points plus the count guards). Executed on the main
thread, in dependency order: implement module -> wire four remaining touch
points -> write tests -> run full suite -> write `docs/DxMeasured.md`.

## Gate

Fletcher reviewer subagent (`Agent`, `subagent_type: Explore`, read-only),
dispatched against the working tree before commit. Report: `01-j-dx-14.md`
in this folder.
