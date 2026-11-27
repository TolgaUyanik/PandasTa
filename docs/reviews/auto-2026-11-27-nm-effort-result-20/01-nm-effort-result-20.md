# Task log — NM-EFFORT-RESULT-20 (issue #185)

## Implementation (main thread)

1. Read the issue's own text, the screen prototype (`docs/issues/screen/ind_screen_r7.py`'s
   `nm_effort_result_20` candidate) and `candidates_r7.csv`'s pre-port Gate E row to confirm the
   formula and the prior overlap measurement.
2. Read the two closest existing ports for template: `nm_mmi_250` (issue #184, Measured.md /
   measure-script shape, `MIN_LENGTH` reasoning) and `g191_144` (issue #57, multi-input
   `high`/`low`/`volume` wiring, dual-axis price/volume/combined Gate D, future-splice Gate B
   harness).
3. Wrote `pandas_ta/volume/nm_effort_result_20.py`: `rel_volume = V/SMA20(V)`,
   `rel_range = (H-L)/SMA20(H-L)`, `NM_EFFORT_RESULT = rel_volume/rel_range`, each division masked
   independently (`inf -> NaN`), matching the prototype's nested `sdiv` calls. `MIN_LENGTH = 2`
   (length=1 forces both ratios to 1.0 by construction).
4. Wired all five touch points: `pandas_ta/volume/__init__.py` (export), `pandas_ta/__init__.py`
   (`Category["volume"]`, alphabetically between `mfi` and `nvi`), `pandas_ta/core.py` (accessor),
   `tests/test_nm_effort_result_20.py` (37 tests).
5. Wrote `tests/test_nm_effort_result_20.py`: Gate A (hand-derived 4-bar fixture at length=2,
   independent scalar-loop cross-check), `MIN_LENGTH` forced-constant probes, Gate B (future-splice
   sweep + two mutants: `write-shift`, `forward-mean-volume`), Gate C (reachability, flat-window
   blanking), Gate D (price/volume/combined x8/x64 bit-identical, x10/x3.7 tolerance), wiring.
6. Ran the tests, found and fixed four off-by-one assumptions in my own test file (warm-up is
   `length - 1`, not `length`, matching pandas' `rolling(length, min_periods=length)` convention;
   a `length`-bar input already yields one valid output, not `None`).
7. Regenerated `docs/IndicatorDictionary.md` (`python docs/gen_indicator_dictionary.py`); the
   generator classified the new column `SF` automatically.
8. Updated README (419→420 registered, 427→428 callable, `volume (48)`→`(49)` with the name added
   alphabetically), `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 420,
   `CATEGORY_BUCKETS["volume"]` 49), `docs/MLCompanionContract.md` (765 tagged / 390 `SF`, new
   chain entry).
9. Wrote and ran `docs/measure_nm_effort_result_20.py` and `docs/measure_nm_effort_result_20_cpu.py`,
   transcribed every number into `docs/NmEffortResult20Measured.md`.

## Gate (Fletcher reviewer, round 1)

Dispatched a read-only `Explore` subagent with the Fletcher persona and the full file list,
instructed to independently re-run the tests and measurement script and hand-recompute the Gate A
fixture.

```
VERDICT: PASS
FINDINGS:
  (none)
SUMMARY: Every claim in this port checks out against an actual run, not an invented number -- I
re-ran `tests/test_nm_effort_result_20.py` (37 passed), `python docs/measure_nm_effort_result_20.py`
(Gate A/B/C/D numbers bit-identical to the ones transcribed into `docs/NmEffortResult20Measured.md`),
the CPU-variant script (37 passed, correct AVX set reported), the full seven-module verify command
(1,775 passed, 1 failed, 7 skipped -- the single failure is exactly
`test_every_indicator_that_needs_a_row_has_one` for `['nm_effort_result_20']`, the explicitly
expected Gate E owed state), and hand-recomputed the four-bar Gate A fixture by hand (1.0, 15/7,
0.8 -- all correct). The Gate A disclosure is honest (there genuinely is no second source formula;
the issue's own text says so), Gate B's two mutants are genuine look-ahead constructions caught by
a real future-splice sweep (not prefix truncation), the dual-axis Gate D algebra is correct and its
1e-6 tolerance sits at a margin above the measured noise (~1.3e-9 to ~4.7e-9) consistent with this
repo's other ports' margin conventions and with the issue-solver's own CPU-variance rule against
pinning near 1e-6. `MIN_LENGTH=2`'s forced-constant argument is arithmetically sound and
empirically confirmed. All five wiring touch points are present, alphabetically correct (`mfi` ->
`nm_effort_result_20` -> `nvi`), and every touched counter (README 420/428/volume(49),
`IndicatorDictionary.md` 422/420/428/volume(50), `MLCompanionContract.md` 765/390) is internally
consistent and matches a live regeneration/measurement. No file outside the allowed scope was
touched, the ledger is untouched, and Gate E is correctly left pending with no invented verdict.
Nothing here needed fixing.
```

PASS on round 1 — no REVISE rounds needed.
