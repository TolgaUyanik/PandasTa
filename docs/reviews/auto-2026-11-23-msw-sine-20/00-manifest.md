# Mode C manifest — TL-MSW-SINE-20 (issue #146)

## Task

Single free-form task, taken verbatim from the invocation:

> TL-MSW-SINE-20: port the indicator of issue #146 through Gates A-D, the wiring, the tests and
> docs/<Name>Measured.md, per the issue and the rules in your system prompt (MESA sine wave,
> fixed-period DFT form (20). Source: Tulip Indicators (LGPL-3.0) — `msw.c: sin(phase)`.). Gate E
> and the whole suites are run by the launcher afterwards.

## Phase 2 — clarify

Checked: goal, scope, and "done" criterion are all actionable as written — the issue (#146) gives
the published source (Ehlers' MESA Sine Wave, fixed-period DFT form), the period (20), the guard
(scale-free 0.001*close, issue's explicit instruction), and the sister port (#145 `msw_lead`,
already merged) gives a byte-for-byte template for the phase arithmetic, tests, docs, and wiring
shape. No gaps found. No questions asked.

## Phase 3 — execution map

One task, non-parallel, main thread: a single indicator port touching the same ~12 files the
sister port touched, done end-to-end before any review.

| Task | Lane | Why |
|---|---|---|
| TL-MSW-SINE-20 | main thread | single coherent port; no independent sub-scopes to split |

## Files touched

- `pandas_ta/cycles/msw_sine.py` (new)
- `pandas_ta/cycles/__init__.py` (import added)
- `pandas_ta/core.py` (accessor added)
- `pandas_ta/__init__.py` (Category entry added)
- `tests/test_msw_sine.py` (new, 12 tests: mutant + scale present)
- `docs/measure_msw_sine_proxy.py` (new)
- `docs/measure_msw_sine_cpu.py` (new)
- `docs/MswSineMeasured.md` (new)
- `tests/test_altport2_ports.py` (CATEGORY_TOTAL 378 -> 379)
- `docs/MLCompanionContract.md` (723 -> 724 tagged, 357 -> 358 SF)
- `docs/IndicatorDictionary.md` (regenerated via `python docs/gen_indicator_dictionary.py`)
- `README.md` (headline 378 -> 379, accessor count 386 -> 387, cycles (10) -> (11) + name)

Gate E and the ledger row are explicitly out of scope for this session (launcher runs Gate E;
a later receipt session records the row) — `docs/MswSineMeasured.md` says so, and
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` fails accordingly
(expected).
