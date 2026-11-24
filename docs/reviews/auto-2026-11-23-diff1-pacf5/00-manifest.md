# Manifest — auto-2026-11-23-diff1-pacf5

## Task

Single task, resolved from the `/brutally-honest-review --auto` invocation (free-form
task description, Mode C):

> KATS-DIFF1-PACF5-100: port the indicator of issue #151 through Gates A-D, the wiring,
> the tests and `docs/<Name>Measured.md`, per the issue and the rules in the session's
> system prompt (sum of squares of the first 5 return partial autocorrelations (100).
> Source: Kats tsfeatures (Meta, MIT) — `get_acfpacf_features: diff1y_pacf5 =
> sum(pacf(diff(x))[1:6]^2)`.). Gate E and the whole suites are run by the launcher
> afterwards.

## Clarifications (Phase 2)

None needed. The issue text and the session's system-prompt overrides (Gate E deferred
to the launcher, restricted test subset, no network access, file-scope limits) fully
specify scope and "done". One ASSUMPTION was made during implementation, logged in the
task file below: the exact statsmodels `pacf` method matching the issue's "Durbin-
Levinson on the unadjusted ACF" was not stated in the issue, so it was determined by
measurement (`docs/measure_diff1_pacf5.py`, `pacf_method_probe`) rather than guessed —
`method="ywm"` matches to 1e-17, `method="ywadjusted"` (the historical default) does not.

## Execution map (Phase 3)

One task, no parallelism: main-thread implementation (file-scope overlaps the shared
wiring files `pandas_ta/__init__.py`, `pandas_ta/core.py`, `README.md`,
`docs/MLCompanionContract.md`, `tests/test_altport2_ports.py`, which a concurrent task
would race on; there was only one task here regardless).

## Gate (Phase 4)

One Fletcher reviewer round (Explore agent, read-only, Bash-enabled to actually run the
tests and measurement scripts rather than trust the diff). Verdict: **PASS**, round 1,
no findings. Full verdict in `01-diff1-pacf5.md`.
