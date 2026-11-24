# Task: fix round-1 review findings on `tdi` (issue #148)

## Implementation (main thread)

1. **MAJOR fix** — ran `python docs/measure_tdi.py W W2` at HEAD. Live output:
   `Category` total **387**, tagged columns **732** (`SF` **366**, among
   `PX2:2 PX:137 SF:366 BIN:104 ORD:59 CONST:43 ??:21`). Rewrote
   `docs/TdiMeasured.md`'s `§W Wiring` section from 380 / 724→725 / 358→359 to
   387 / 731→732 / 365→366, citing the script and date.
2. **MINOR fix** — confirmed the live ledger row via
   `grep -n "tdi" docs/gate_e_ledger.csv`: `is148-tdi-b1bb91c6`, measured
   2026-11-24, figures unchanged (0.4924 / 0.4915 / n=391,017 / 398,849 bars /
   329+358). Repointed the run id/date in `tests/test_tdi.py` (Gate E
   docstring clause), `docs/MLCompanionContract.md` (#148 clause), and
   `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` comment, #148 clause)
   from `is148-tdi-a3774479` / 2026-11-23 to `is148-tdi-b1bb91c6` / 2026-11-24.
3. **NIT fix** — `tests/test_tdi.py::test_scale_fires_strictly_between_zero_and_n`
   reparametrized from `FIRING` to `NAMES` (all 8 frames, `flat` included).
4. **NIT fix** — diffed `README.md`'s trend list against the merge-base copy
   (`git merge-base HEAD dev` → `9b964a8480d93bf8d54ace2d5cbac23d0173d33e`),
   confirmed `fvg`/`fvg_sweep_magnet`, `vstop`/`vstop2`, `zigzag`/`zigzag_fib`
   were alphabetical there and swapped in the current branch; restored
   alphabetical order on all three pairs. `tdi`'s own insertion point (between
   `swing_equilibrium` and `triangle_wedge`) was already correct and untouched.
5. Added a "Round 6 (review fix)" section to `docs/TdiMeasured.md` narrating
   all four fixes with the measured numbers, following the file's own
   per-round convention (Rounds 2-5 above it).

## Verification

`python -m pytest -q tests/test_tdi.py tests/test_readme_counts.py
tests/test_altport2_ports.py tests/test_wiring_accessors.py
tests/test_ml_companions.py tests/test_gate_e_ledger.py
tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py` →
**1,599 passed, 7 skipped, 0 failed** (measured 2026-11-24, after the edits).

No code under `pandas_ta/` changed in this round (docs/tests/README only), so
no CPU-kernel re-run (`docs/measure_tdi_cpu.py`) was needed beyond the one
already recorded in Round 3/5.

## Review round 1

VERDICT: PASS

FINDINGS: none.

SUMMARY (quoted verbatim from the reviewer): "Every finding from round 1 was
fixed correctly and nothing was broken in the process — the §W numbers now
match a live `measure_tdi.py W W2` run (387 / 731->732 / 365->366) and
cross-check against the ledger row `is148-tdi-b1bb91c6` and
`IndicatorDictionary.md`'s `TDI_20_2 SF` tag; all three run-id citations are
repointed to `b1bb91c6`/2026-11-24 with figures untouched; the
`test_scale_fires_strictly_between_zero_and_n` reparametrization to `NAMES`
was verified by actually running it (8/8 pass, `flat` included, `0 < fires <
n` holds); README's three pairs are alphabetical again and verified against
the merge-base copy exactly as claimed; the full targeted suite reproduces
the doc's exact claim of 1,599 passed / 7 skipped / 0 failed; remaining
`a3774479`/`380` greps are confined to the Round 3/4/6 historical narrative
describing the bug that was fixed, not live claims."

**Status: DONE.** PASS on round 1 — no re-dispatch needed.
