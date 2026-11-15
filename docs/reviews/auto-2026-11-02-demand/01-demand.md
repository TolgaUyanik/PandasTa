# Task: demand (issue #33) — Gates A-D, wiring, tests, docs/DemandMeasured.md

## Implementation (round 1)

- `pandas_ta/volume/demand.py`: new module. `K = 3*close/SMA(length)(rolling(2).max(high-low))`,
  `pct_chg = close.pct_change()`, rising/falling/flat branch per the issue's formula, output
  `(BP-SP) / SMA(volume, vol_length)`.
- Wired at all five touch points: `pandas_ta/volume/__init__.py`, `pandas_ta/__init__.py`
  (`Category["volume"]`), `pandas_ta/core.py` (`AnalysisIndicators.demand`),
  `tests/test_demand.py`.
- `README.md` (267->268 headline, 275->276 accessor count, `volume (28)`->`(29)` + name),
  `docs/IndicatorDictionary.md` (regenerated), `docs/MLCompanionContract.md` (613->614
  tagged, 258->259 `SF`), `tests/test_altport2_ports.py` (`CATEGORY_TOTAL`/`CATEGORY_BUCKETS`)
  all updated and checked by their respective tests.
- `docs/DemandMeasured.md` + `docs/measure_demand.py`: receipt, Gate A's "primary source
  unavailable" disclosure, Gates B/C/D numbers, Gate E marked pending.
- Full local suite before review: 3 failed (all pre-existing/expected per issue-solver
  rules: `test_pine_coverage_csv` known break, `test_altrepo_talib_csv` needs sibling repo,
  `test_gate_e_ledger` Gate E owed), 4061 passed, 83 skipped.

## Review round 1

Dispatched Fletcher (`Explore` subagent, read-only) against `pandas_ta/volume/demand.py`,
`tests/test_demand.py`, `docs/DemandMeasured.md`, the wiring diffs, `README.md`,
`docs/MLCompanionContract.md`, `tests/test_altport2_ports.py`, `docs/measure_demand.py`.

**VERDICT: REVISE**

```
FINDINGS:
  - severity: CRITICAL
    location: pandas_ta/volume/demand.py:34-49 (flat branch), docstring line 140
    problem:  The flat (pct_chg == 0) branch sets bp = sp = volume unconditionally and
      never checks whether k (3*close/range_sma) has itself finished warming up.
      raw.where(pct_chg.notna()) only masks "no previous bar"; at the shipped DEFAULT
      length=vol_length=10, avg_vol is first valid at row 9 but k is first valid at row 10
      -- a 1-row gap. If close[9]==close[8] exactly (the issue's own named ΔC=0 failure
      mode), the flat branch fires, raw=0.0 never touches the NaN k, and out[9] reads a
      fabricated non-NaN 0.0 instead of "undefined, insufficient history". With
      vol_length < length (e.g. 50/5) this is a 46-row window, not a one-row fluke. The
      module docstring's "Returns" claim ("NaN wherever range_sma or avg_vol is not yet
      defined") is false in this window. No existing test catches it: the one test built
      to probe the guard uses length=vol_length=1, where the gap coincides with pct_chg's
      own NaN row by coincidence.
    fix:      Mask on pct_chg.notna() & k.notna(), and add regression tests at asymmetric
      parameters with an engineered flat close placed inside the gap window.

  - severity: MINOR
    location: docs/DemandMeasured.md:54
    problem:  Gate C's "10 NaN bars are exactly the combined warm-up" claim is seed-lucky
      given the CRITICAL bug, not an invariant.
    fix:      Resolved once the CRITICAL fix lands; otherwise note the caveat.

SUMMARY: Everything else -- wiring, README/dictionary/contract counts, the two hand-derived
bars, the mutant's liveness-then-capture structure, Gate D's independent-axis scale tests,
and the honest "Gate A unverifiable" disclosure -- was done correctly. But the one thing
this review was told to trace by hand (whether the ΔC-near-zero guard distinguishes
warm-up from genuinely flat) fails under the module's own defaults: row 9 can read a
fabricated 0.0 instead of NaN whenever the close repeats, exactly the tick-rounding
scenario the issue describes, and the one test meant to catch it is parameterized so it
cannot see the bug. Fix the mask, add the asymmetric-length test, and this ships.
```

## Fix applied

`pandas_ta/volume/demand.py`: changed `raw = raw.where(pct_chg.notna())` to
`raw = raw.where(pct_chg.notna() & k.notna())`, with an expanded comment explaining the
differential warm-up rates of `k` (range_sma) and `avg_vol`.

Added two regression tests to `tests/test_demand.py`:
- `test_flat_bar_inside_the_k_warmup_gap_is_nan_not_zero` (default `length=vol_length=10`,
  engineered flat close at index 9 -- the exact 1-row gap the finding named).
- `test_flat_bar_inside_an_asymmetric_k_warmup_gap_is_nan_not_zero` (`length=50,
  vol_length=5`, engineered flat close at index 20 inside the 46-row gap).

Re-ran `tests/test_demand.py`: 16 passed (14 + 2 new). Re-ran `python docs/measure_demand.py`:
every number unchanged from the pre-fix run (no flat bar in the seed-17 walk happened to
land inside the 1-row default gap) -- the bug was real but not exercised by that particular
measurement, confirming the fix (not luck) is what rules it out going forward. Re-ran the
full suite: 3 failed (same three pre-existing/expected), 4063 passed (+2), 83 skipped.
Updated `docs/DemandMeasured.md` with a "Round 1 review fix" section and the new test count.

## Review round 2

Re-dispatched Fletcher (`Explore` subagent, read-only) against the fixed
`pandas_ta/volume/demand.py` and `tests/test_demand.py` (now 16 tests), told to verify the
round-1 fix by hand, not take the narrative on trust.

**VERDICT: PASS**

```
FINDINGS:
  (none -- the round-1 CRITICAL is actually fixed, not just plausibly fixed)

Verification performed, not just read:
- Hand-traced warm-up rates at length=vol_length=10: two_bar_range (rolling(2).max of
  high-low) is NaN at index 0, valid from index 1; range_sma = two_bar_range.rolling(10)
  .mean() needs indices 1-10 clean, so NaN at index 9, first valid at index 10 -- confirming
  k is NaN at row 9, valid at row 10. avg_vol = volume.rolling(10).mean() has no leading NaN
  in volume, valid from index 9. That's the exact 1-row gap the fix targets.
- Confirmed pct_chg.notna() & k.notna() masks row 9 to NaN at those defaults, and confirmed
  a genuinely flat bar OUTSIDE any gap (test_unchanged_close_reads_exactly_zero, index 3,
  length=vol_length=1) is untouched -- k is already valid there, output stays exactly 0.0.
- Checked rising/falling for a false regression: when k is NaN, denom=k*pct_chg is NaN,
  safe_denom stays NaN (NaN != 0 -> True, .where keeps it), volume/safe_denom is NaN -- raw
  was ALREADY NaN on those branches before the fix. The added & k.notna() term is provably
  a no-op there, not a new source of false NaNs. No regression.
- Re-derived the gap-width formula independently (gap exists iff vol_length <= length, width
  = length - vol_length + 1): 1 row for 10/10 (index 9), 46 rows indices 4-49 for 50/5 --
  both new tests' engineered flat-bar placements (index 9, index 20) land inside the claimed
  gap, not by coincidence, and both series satisfy verify_series's min_len = max(length,
  vol_length)+2 (12 and 52, with n=15 and n=60), so neither test accidentally passes because
  verify_series rejected the series outright.
- Ran pytest tests/test_demand.py -v: all 16 pass, including the two new regression tests
  and all 14 original ones (hand-derived bars, causality mutant at 31/31, scale-free
  x8/x64/x10/x3.7 on both axes, wiring). Nothing in the original suite's pinned values
  depends on a row where k is NaN but was previously non-masked, so none of it was disturbed.
- docs/DemandMeasured.md's Gate C claim ("10 NaN bars are exactly the combined warm-up,
  max(length, vol_length)") is now a true invariant under the fix, not the seed-lucky
  coincidence round 1 flagged -- the doc's "Round 1 review fix" section states this
  correctly.

SUMMARY: The mask fix is correct by hand-derivation, not merely by the two tests agreeing
with the code that produced them -- the differential warm-up arithmetic checks out exactly,
the rising/falling branches were already NaN-safe so the added term changes nothing there,
and both new regression tests land their engineered flat bar genuinely inside the claimed
gap rather than tripping some unrelated verify_series rejection or coincidental NaN. Nothing
else regressed. This is the rare case where the round-1 fix actually earns the clean bill --
ship it.
```

Final state and summary table: `99-summary.md`.
