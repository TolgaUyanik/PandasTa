# Run manifest — TDI round-1 review fixes

**Invocation:** `/brutally-honest-review --auto "Fix every CRITICAL and MAJOR finding
of the pre-push review gate (round 1 of 3, HEAD 9fddc227df6e)..."` — Mode C
(free-form single task), no `--refute`.

**Task (as given):** Fix every CRITICAL and MAJOR finding of the pre-push review
gate (round 1 of 3, HEAD `9fddc227df6e`), quoted verbatim in the invocation;
fix MINOR/NIT findings only when cheap and safe.

**Source review (verbatim contract), VERDICT: REVISE:**
- MAJOR — `docs/TdiMeasured.md` §W Wiring: `Category` total stated as 380 and
  census as 724→725 / 358→359 `SF`, copied from a different port's receipt
  (`docs/TtrSnr20Measured.md`, issue #149). Live values differ.
- MINOR — `tests/test_tdi.py`, `docs/MLCompanionContract.md`'s #148 clause,
  `tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` comment: all three cite a
  stale Gate E run id `is148-tdi-a3774479` (2026-11-23), superseded by
  `is148-tdi-b1bb91c6` (2026-11-24) in the current ledger.
- NIT — `tests/test_tdi.py::test_scale_fires_strictly_between_zero_and_n`
  parametrized over `FIRING` (excludes `flat`) with no stated reason.
- NIT — `README.md` trend list: unrelated ordering churn on three pairs
  (`fvg`/`fvg_sweep_magnet`, `vstop`/`vstop2`, `zigzag`/`zigzag_fib`).

## Phase 2 — Clarify

No gaps: the task names its own fixes exactly. No AskUserQuestion round
needed (and the tool is unavailable in this issue-solver session regardless).
No assumptions logged.

## Phase 3 — Execution map

Single task, overlapping file scope (`docs/TdiMeasured.md`, `tests/test_tdi.py`,
`docs/MLCompanionContract.md`, `tests/test_altport2_ports.py`, `README.md`) and
needs main-context judgment (running `docs/measure_tdi.py`, reading the ledger,
diffing against the merge-base `README.md`) — run on the **main thread**, not a
parallel subagent lane.

See `01-tdi-fixes.md` for the implementation log and `99-summary.md` for the
outcome table.
