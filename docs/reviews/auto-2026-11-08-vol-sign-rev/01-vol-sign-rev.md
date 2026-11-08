# Task: vol_sign_rev port — log

## Implementation

- `pandas_ta/volume/vol_sign_rev.py`: `VSR = sign(volume.diff(1)) * -(close/close.shift(1) - 1)`.
  Alpha#12 of Kakushadze (2016), scale-free form per the issue's own `delta(close,1) ->
  one-bar return` conversion.
- Wired: `pandas_ta/volume/__init__.py` (export), `pandas_ta/__init__.py`
  (`Category["volume"]`), `pandas_ta/core.py` (`df.ta.vol_sign_rev()` accessor),
  `tests/test_vol_sign_rev.py` (15 tests: correctness, causality mutant, scale-free,
  wiring).
- `docs/measure_vol_sign_rev.py`: synthetic measurement script; output transcribed into
  `docs/VolSignRevMeasured.md`.
- `docs/IndicatorDictionary.md` regenerated (`python docs/gen_indicator_dictionary.py`).
- `docs/MLCompanionContract.md`: running SF-tag-count sentence updated (619 -> 620 total,
  263 -> 264 `SF`), per `tests/test_ml_companions.py`.
- `README.md`: indicator counts (274 -> 275, accessor 282 -> 283) and the `volume (31)`
  category row updated.
- `tests/test_altport2_ports.py`: `CATEGORY_TOTAL` 274 -> 275, `CATEGORY_BUCKETS["volume"]`
  30 -> 31.

## Measurements (this session)

- Gate A: hand-derived 5-bar example matches module output exactly; translation from the
  issue's formula is literal (`delta(x,1) = x.diff(1)`, `sign(x) = np.sign(x)`), with one
  disclosed substitution (the issue's own scale-free conversion).
- Gate B: future-perturbation sweep, 45 offsets past the 1-bar warm-up — real module 0/45
  leaks; an 8-bar... (1-bar) look-ahead mutant (`close.shift(1)` -> `close.shift(-1)`)
  caught 45/45.
- Gate D: price scale x8/x64 bit-identical (0.0 max diff), x10/x3.7 within 2.22e-16;
  volume scale x8/x64/x10/x3.7 all bit-identical (0.0 max diff, sign is scale-invariant
  for any positive scalar).
- Gate C (synthetic reachability): 899/900 bars fire (99.89%), 899 distinct values.
- `python -m pytest -q` (this session): 3 failed, 4218 passed, 83 skipped — the 3
  failures are the repo's documented pre-existing/expected ones (`test_pine_coverage_csv`,
  `test_altrepo_talib_csv`, `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  — this port's row is owed, recorded by a future receipt session).

## Review round 1

Dispatched a Fletcher reviewer (`Explore` subagent, read-only) against the full diff with
the original user ask verbatim and an explicit file list (module, tests, measured doc,
measure script, and all 7 wiring/count/docs files).

VERDICT: PASS

FINDINGS:
- severity: NIT
  location: tests/test_vol_sign_rev.py:104 / docs/measure_vol_sign_rev.py:52 (OFFSETS/offsets)
  problem: The 45-offset sweep (`range(5, 895, 20)`) is a reasonable sample but its stride
    is never justified beyond "past the 1-bar warm-up".
  fix: No action required to ship; if a future port's mutant has a narrower reach than
    "every bar from j onward," switch the stride to 1.
- severity: NIT
  location: pandas_ta/volume/vol_sign_rev.py:9-10
  problem: `verify_series(close, 2)` / `verify_series(volume, 2)` hard-codes a minimum
    length of 2 without a comment explaining why.
  fix: Add a one-line comment noting `delta(.,1)` needs 2 bars.

SUMMARY (verbatim): "This is a clean, honest Gate A-D port. The arithmetic was redone by
hand and matches both the test's claimed numbers and the module's actual output; the
causality mutant test is a real look-ahead (reads close[t+1] via close.shift(-1)) and the
future-perturbation sweep correctly isolates bars before the perturbation index, catching
it at 45/45 while the real module leaks 0/45, confirmed by re-running both the test suite
and docs/measure_vol_sign_rev.py directly — every number printed by the script matches the
doc verbatim. The scale-free claims are correct and distinguish exact bit-identity (powers
of two, ratio cancels exactly) from tolerance-bound cases (non-power-of-two scalars)
exactly as CLAUDE.md's Gate D requires, and the volume-sign invariance claim is
mathematically sound and empirically confirmed at all four tested scalars. All five wiring
touch points are present and mutually consistent, `VSR` collides with nothing else in the
package, Gate E is correctly left pending rather than fabricated, and the full suite run
(3 failed/4218 passed/83 skipped) matches the known, pre-existing failures plus the
expected 'Gate E owed' skip for this new indicator. The diff is surgical — nothing touched
outside the five wiring points plus the count-bookkeeping files. No CRITICAL or MAJOR
findings; ship it."

## Fixes applied (no re-review needed — both NITs, no CRITICAL/MAJOR)

Applied the second NIT's fix: added `# min length 2: delta(.,1) needs 2 bars` next to both
`verify_series` calls in `pandas_ta/volume/vol_sign_rev.py`. Re-ran
`tests/test_vol_sign_rev.py` — still 15/15 passing. The first NIT needed no code change per
the reviewer's own note ("No action required to ship").

## Status: PASS (round 1)
