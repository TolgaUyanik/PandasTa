# Mode C manifest -- ADXR port (issue #110 / LEAN-ADXR-14)

## Task

Single free-form task, as given in the invocation:

> LEAN-ADXR-14: port the indicator of issue #110 through Gates A-D, the
> wiring, the tests and docs/<Name>Measured.md, per the issue and the rules
> in your system prompt (ADXR, average directional movement rating (14).
> Source: QuantConnect Lean (Apache-2.0); also jesse adxr --
> AverageDirectionalMovementIndexRating.cs: (ADX + ADX[n]) / 2.). Gate E and
> the suites are run by the launcher afterwards.

Source: `docs/issues/screen/ind_screen_r2.py:86-90` (candidate `lean_adxr_14`),
issue #110 body (verbatim in the system prompt).

## Clarifications (Phase 2)

None asked. `AskUserQuestion` is unavailable in this headless issue-solver
session; the issue text and this repo's `CLAUDE.md` porting protocol fully
specify scope, gates and done-when criteria, so no ambiguity needed
resolving. One ASSUMPTION made, conservative reading:

- **ASSUMPTION:** ADXR is built on this fork's own already-shipped `adx()`
  (Wilder RMA) rather than re-deriving DI+/DI-/DX from the prototype's
  `dm_wilder`/`dx_wilder` helpers. Smaller blast radius (no new DX/DM math to
  get wrong; `adx()`'s own correctness is already upstream and out of scope),
  and it is a direct, literal application of the Lean source formula
  `(ADX + ADX[period]) / 2` rather than a transliteration of the prototype.

## Execution map (Phase 3)

Single task, non-parallelizable (it touches the shared wiring files
`pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_altport2_ports.py`,
`README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md` --
all five wiring touch points plus the count guards). Executed on the main
thread, in dependency order: implement module -> wire four remaining touch
points -> write tests -> run full suite -> write `docs/AdxrMeasured.md`.

## Gate

Fletcher reviewer subagent (`Agent`, `subagent_type: Explore`, read-only),
dispatched against the committed diff (commit `a8ed3c0`). Report:
`01-adxr-port.md` in this folder.
