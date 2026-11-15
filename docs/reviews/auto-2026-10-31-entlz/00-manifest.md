# Mode C manifest — ENTLZ (issue #11)

## Task

> ENTLZ: port the indicator of issue #11 through Gates A-D, the wiring, the tests and
> docs/<Name>Measured.md, per the issue and the rules in your system prompt (encode returns
> as a symbol sequence (sign, or quantile bins) and estimate its entropy over). Gate E and
> the suites are run by the launcher afterwards.

One task, free-form (not a TODO tag). Resolved as: port `entlz`, a plug-in Shannon-entropy
column over sign-encoded returns, into `pandas_ta/statistics/`, through Gates A, B, D (C
synthetic only; E deferred to the launcher per the issue-solver system prompt's override).

## Clarify

AskUserQuestion is unavailable (headless issue-solver session; no human answers). Per the
system prompt's override, gaps were resolved with the most conservative (smallest-scope)
reading and logged as ASSUMPTIONs in `docs/EntlzMeasured.md` ("Decisions the issue left
open"):

1. Encoding: sign (not k quantile bins) — no fit-on-past-data surface to prove causal.
2. Estimator: plug-in (not Lempel-Ziv / Kontoyiannis) — issue states plug-in is simplest.
3. Window: `length=20` — matches this fork's short-lookback defaults; not tuned.
4. Alphabet: 3 symbols (`{-1, 0, +1}`, from `np.sign`) — avoids inventing a flat-tie rule.

No questions asked; none needed beyond the above, which is recorded, not silently assumed.

## Execution map

Single task, main thread (not parallel-subagent-eligible): it touches shared counters
(`README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`,
`tests/test_altport2_ports.py`) that need the surrounding context of the whole wiring change,
plus main-context judgment on the math/causality design. File scope:

- Add: `pandas_ta/statistics/entlz.py`, `tests/test_entlz.py`, `docs/EntlzMeasured.md`,
  `docs/measure_entlz_proxy.py`.
- Modify: `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`,
  `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`,
  `tests/test_altport2_ports.py`.

## Status at gate time

- `tests/test_entlz.py`: 22/22 passing (round 2 added 3 tests: a non-default-base reference
  check, and a pinned counter-example demonstrating why Gate B uses a deterministic
  single-bar flip instead of the repo's usual whole-tail-replacement convention).
- Full suite with CI's two `--deselect`s: 1 failed (`test_gate_e_ledger.py` for `entlz`,
  expected — Gate E is pending), 3,523 passed, 83 skipped.
- Gate E and both repos' suites are explicitly NOT run here (launcher's job, per the
  issue-solver system prompt overriding the issue's own gate table).

## Review rounds

- Round 1 (Fletcher/Explore): REVISE — one MAJOR (an unreproducible "pilot run... showed
  29/32" number in docs/EntlzMeasured.md's Gate B row with no backing test or script) and
  two NITs (no non-default-`base` test; a 3x rolling pass that's fine to leave as-is).
  Fixed: added `test_the_random_future_convention_ties_on_this_alphabet` (pins 29/32
  reproducibly) and `test_matches_the_reference_loop_at_a_non_default_base`; reworded the
  Gate B row to cite the test by name instead of asserting a bare number.
- Round 2 (Fletcher/Explore): REVISE — one MAJOR (the round-1 fix added 3 tests but the doc's
  own "19 of 19 passing" and the Gate F suite totals were not re-measured afterward, so both
  went stale by exactly the tests just added). Fixed: re-ran `tests/test_entlz.py` (22/22)
  and the full suite with CI's deselects (1 failed, 3,523 passed, 83 skipped, 2 deselected),
  updated both numbers in `docs/EntlzMeasured.md` and this manifest.
