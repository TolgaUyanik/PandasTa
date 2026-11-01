# Run manifest — EHLERS (issue #30), 2026-11-01

## Original ask

> EHLERS: port the indicator of issue #30 through Gates A-D, the wiring, the tests and
> docs/<Name>Measured.md, per the issue and the rules in your system prompt (a family,
> screened and ported one by one. Scale-free forms only.). Gate E and the suites are run by
> the launcher afterwards.

## Resolved task

One task: port one indicator from the Ehlers DSP family named in issue #30, screen the rest,
through Gates A-D, wiring, tests, and `docs/<Name>Measured.md`. Gate E (the private
Backtesting engine) and both repos' full suites are explicitly out of scope for this session
per the issue-solver system prompt's override rules.

## Clarification (Phase 2)

No AskUserQuestion available in this headless session (issue-solver rule). Gaps resolved by
the most conservative reading, logged as ASSUMPTIONs rather than asked:

- **ASSUMPTION 1 — which indicator to build.** The issue names ~13 candidates across one
  table row each. The repo's porting rules cap a session at 3 new
  `pandas_ta/<category>/*.py` files, and the issue itself says "screened and ported one by
  one". Read "one by one" as literally one indicator fully through Gates A-D per session, not
  the whole family. Picked **Correlation Cycle**: the issue's own pre-registered note says
  it and Reflex/Trendflex have "the best chance" to ship, and unlike Reflex/Trendflex or the
  Roofing-Filter family, it is NOT a recursive filter (no SuperSmoother/highpass cascade,
  which CLAUDE.md explicitly flags for `ssf`'s own negative-index causality bug on first
  implementation) — lower risk for a single unsupervised session.
- **ASSUMPTION 2 — no source is reachable.** No web access, no Pine corpus, no
  `jesse-ai/jesse` checkout in this environment. Per CLAUDE.md, Correlation Cycle's only
  possible Gate A reference is "Ehlers' papers or a library's source" — neither reachable.
  Followed the `pfe` precedent (`docs/PfeMeasured.md`): Gate A is self-consistency against an
  independently-derived closed-form identity, not a line-by-line citation, with the gap
  disclosed in the module docstring and the measured-numbers doc.
- **ASSUMPTION 3 — market state sub-output.** The issue's row is "Correlation Cycle (angle +
  market state)". Ehlers' exact market-state classification formula is not independently
  verifiable here; inventing thresholds and labeling them Ehlers' would not be a port.
  Shipped Real/Imag/Angle only; market state skipped with a one-line reason in
  `docs/EhlersDspMeasured.md`.
- **ASSUMPTION 4 — window-lag convention.** Ehlers' own convention for which end of the
  rolling window is "lag zero" is not verifiable here either. Used the same oldest-first
  convention already shipped and tested in this fork's own `linreg(r=True)` (which `cti`
  wraps), disclosed in the docstring as a deliberate, not-necessarily-Ehlers-matching choice.

## Execution map

Single task, main thread (sequential: module, wiring, tests, docs, doc-count fixups, full
suite, review, commit). No parallel lanes — one indicator, one dependency chain.

## Gate

Fletcher reviewer dispatched against the diff below. Verdict and rounds in
`01-correlation-cycle.md`.

## Files touched

- `pandas_ta/cycles/correlation_cycle.py` (new)
- `pandas_ta/cycles/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py` (wiring)
- `tests/test_correlation_cycle.py` (new)
- `docs/CorrelationCycleMeasured.md`, `docs/EhlersDspMeasured.md` (new)
- `docs/measure_correlation_cycle_proxy.py` (new)
- `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`,
  `tests/test_altport2_ports.py` (count fixups)
