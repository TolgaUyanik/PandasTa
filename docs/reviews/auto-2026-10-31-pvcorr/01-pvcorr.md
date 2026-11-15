# Task 01 — pvcorr (issue #18)

## Implementation summary

Ported PVCORR as `pandas_ta/volume/pvcorr.py`: rolling Pearson correlation of the bar return
(`close.pct_change()`) against the change in log volume (`log(V[t]/V[t-1])`, masked to NaN
at non-positive volume rather than qlib's `log(V/V-1+1)`, for exact scale-invariance and a
defined zero-volume policy). Default window 20, column `PVCORR_20`. Wired through all five
touch points (module, `pandas_ta/volume/__init__.py` export, `Category["volume"]`,
`core.py` accessor, `tests/test_pvcorr.py`). Added `docs/measure_pvcorr_proxy.py` and
`docs/PvcorrMeasured.md` with the Gate A-D numbers. Regenerated
`docs/IndicatorDictionary.md`; hand-updated `README.md`, `docs/MLCompanionContract.md`, and
`tests/test_altport2_ports.py`'s category counts (248→249 total, volume 25→26).

Ran locally: `tests/test_pvcorr.py` (18 passed), `tests/test_readme_counts.py`,
`test_altport2_ports.py`, `test_wiring_accessors.py`, `test_ml_companions.py` (106 passed, 3
skipped), `tests/test_gate_e_ledger.py` (142 passed, 1 expected failure —
`test_every_indicator_that_needs_a_row_has_one`, for `pvcorr`, cleared once the launcher's
Gate E run is recorded). Gate E and the full two-repo suites are explicitly the launcher's
job, not this session's.

## Review round 1

Dispatched one Fletcher reviewer subagent (Explore, read-only) against the full diff, with
the original user ask verbatim and an explicit file list (see the dispatch prompt for the
complete background). Verbatim reviewer output:

```
VERDICT: PASS
FINDINGS:
  - severity: MINOR
    location: docs/PvcorrMeasured.md:57 (Gate B row), also docs/PvcorrMeasured.md:20
    problem:  States the causality sweep ran "16 offsets (60..1095, step 65)". The code is `OFFSETS = range(60, 1100, 65)`, which is 60, 125, 190, ..., 1035 — sixteen values ending at 1035, not 1095. 1095 isn't even reachable by that stride from 60. The count (16) is right; the endpoint is a fabricated/miscalculated number sitting in a receipt doc whose entire job is to not have exactly this kind of unmeasured number.
    fix:      Change "(60..1095, step 65)" to "(60..1035, step 65)" in docs/PvcorrMeasured.md line 57 (and double check line 20's "16 offsets" phrasing doesn't repeat the wrong endpoint elsewhere).
SUMMARY: You picked a defensible Gate A variant, gave it a real reason (division-by-zero at halted bars, not a coin flip), and then actually proved it — I ran the suite, the measurement script, and the ledger test myself: 18/18 pvcorr tests pass, the 1.71e-14/5.0e-16/21-extra-NaN/538-642 numbers in the doc all reproduce bit-for-bit, the causality mutants genuinely leak at 16/16 and the real module at 0/16, the scale-free tests correctly separate price-only from volume-only rescale (the part most people would have cut a corner on, since this indicator has two inputs and the issue explicitly warned you'd need to show it on both), the five wiring touch points are consistent, and the CATEGORY_TOTAL/BUCKETS arithmetic checks out exactly against a manual count of the dict (248→249, volume 25→26). The category call (volume over statistics) is argued correctly from the accessor signatures, not asserted. The one thing you let slip through is a number you clearly never ran — the OFFSETS endpoint in the one document whose premise is "every number here was run, not typed." That it's harmless doesn't make it excusable in a doc built to catch exactly that disease. Fix the one line and this would have been clean.
```

**Verdict: PASS.** Gate rule (any CRITICAL/MAJOR → REVISE) not triggered; one MINOR finding.

## Fix applied (post-PASS, no re-review required)

Corrected the stated OFFSETS endpoint in `docs/PvcorrMeasured.md`'s Gate B row from
"60..1095" to the actual "60..1035" (matching `range(60, 1100, 65)`'s last term). Cosmetic;
did not change any test, assertion, or other measured number.

## Status: PASS, round 1
