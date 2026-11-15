# ADXR port -- review round 1

Target: commit `a8ed3c0` (LEAN-ADXR-14: port ADXR, average directional
movement rating (14), as adxr. Refs #110).

## Round 1

```
VERDICT: PASS
FINDINGS:
  (none)
SUMMARY: Clean work. `adxr.py` is exactly `(ADX + ADX[length bars ago]) / 2` computed by calling this fork's own `adx()` — no re-derivation, no edit to `adx.py` — with the shift direction verified correct by a real backward-vs-forward mutant test that is proved live and caught at all 15 swept offsets, and I ran it myself: 13/13 pass. The five wiring touch points are all present and the accessor's kwargs (`length, scalar, mamode, drift, offset`) line up name-for-name with the module signature, no WIRING-1 repeat. Count arithmetic checks out everywhere I verified it by running the actual guard tests rather than eyeballing the diff: `test_altport2_ports.py`'s `CATEGORY_TOTAL`/`CATEGORY_BUCKETS` (238/59), README's three numbers, `MLCompanionContract.md`'s 570→571 tagged / 216→217 SF, and `IndicatorDictionary.md`'s regenerated trend-bucket row — all green under `test_readme_counts.py`, `test_ml_companions.py`, `test_wiring_accessors.py`. `docs/AdxrMeasured.md`'s numbers aren't decoration: I reran `docs/measure_adxr_proxy.py` and the full suite myself and got bit-for-bit the same figures it quotes (859/900 fires, x8 diff 0.0, x10 diff 7.1e-14, 3 failed/3271 passed/83 skipped, all three failures pre-existing and none naming adxr). Gate C is honestly flagged "synthetic only, real-data counts owed," Gate E is honestly "pending," and the ledger/its guard test are untouched as required — all matching the established pattern from KalmanTrend, Pfe, and RangeCompressRun, not a shortcut invented for this port. Docstring attributes both QuantConnect Lean (Apache-2.0) and jesse (MIT) with the exact `.cs` filename and formula. Nothing outside the allowlist was touched, nothing was deleted or renamed. Ship it.
```

Outcome: PASS on round 1. No fixes applied, no re-dispatch needed.
