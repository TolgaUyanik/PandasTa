# Mode C manifest — DEMAND (issue #33)

## Task

> DEMAND: port the indicator of issue #33 through Gates A-D, the wiring, the tests and
> docs/<Name>Measured.md, per the issue and the rules in your system prompt (buying vs
> selling pressure from price change and volume, scaled by recent volatility.). Gate E and
> the suites are run by the launcher afterwards.

Single free-form task, taken as given (no TODO tag, no plan file).

## Clarify (Phase 2)

No AskUserQuestion available in this headless session (issue-solver rules). The issue's own
risks were resolved by the most conservative, smallest-scope reading and logged as
ASSUMPTIONs in `docs/DemandMeasured.md` (Gate A section) and the module docstring's "WHAT IS
ASSUMED":

1. The primary source (book page / Aspray's TASC articles) is not available in this
   worktree — implemented the issue's own formula as given, flagged as unverified against
   the primary source.
2. "max 2-day high-low range" → `rolling(2).max()` of `high - low`.
3. "ΔC/C" → `close.pct_change()` (plain 1-bar percent change).
4. Unchanged close (not addressed by the source) → neutral, `BP = SP = volume`, oscillator
   reads exactly 0 — doubles as the ΔC-near-zero guard the issue asks for.
5. Scale-free: divided by `SMA(volume, vol_length)` (the issue's second option), because raw
   `BP - SP` is linear in volume on every branch, so this choice is exactly invariant under a
   uniform volume rescale (measured, Gate D).

No destructive or out-of-scope steps were needed.

## Execution map

Single task, main thread (file scope: `pandas_ta/volume/demand.py` (new),
`pandas_ta/volume/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`,
`tests/test_demand.py` (new), `README.md`, `docs/IndicatorDictionary.md`,
`docs/MLCompanionContract.md`, `tests/test_altport2_ports.py`, `docs/DemandMeasured.md`
(new), `docs/measure_demand.py` (new) — all within the issue-solver's allowed file list, no
parallel lane needed).

## Gate log

See `01-demand.md`.
