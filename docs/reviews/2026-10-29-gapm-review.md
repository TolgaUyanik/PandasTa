# Brutally Honest Review — gapm port (a0d6b58, cbe3eec)

**Date:** 2026-10-29
**Target:** commits a0d6b58 (feat(momentum): port b2_gapm_40 as gapm, #189) and cbe3eec (test(ml_companions) follow-up) on branch B2-GAPM-40
**Type:** code
**Verdict:** REVISE

## Findings

### MAJOR
- **docs/GapmMeasured.md:28-58, :68-71; a0d6b58 commit body** — The PORT decision cannot be reproduced. On the repo's own `make_df` frame, step-1 screening gave ρ 0.9054 against `TRIXs_18_9`, which is inside the ≥ 0.90 EQUIVALENT band. That result was overruled by a second figure (0.3258 on an "overnight walk") and by the claim "df.ta.gapm() matched the inline formula with ρ 1.0000". Both come from `equiv.py` / `equiv_overnight.py` in an uncommitted scratchpad. The 5-seed NaN-rate rows (31 / 330 / 1,477) and the 328/333 comparator counts have the same problem. Only the single-seed rows could be re-run, and those match exactly. This is the "script never committed" defect that CLAUDE.md warns about three times.
  - Fix: commit both scripts and cite their paths in GapmMeasured.md, or add a test that rebuilds the overnight walk and pins top |ρ| vs TRIX_30_9 / TRIXs_18_9 below 0.80. Make the 5-seed rows reproducible or drop them.

### MINOR / NIT
- **MINOR — pandas_ta/momentum/gapm.py:35-37** — `fill_method` back-fills for any string other than ffill/pad, so a typo silently creates look-ahead. Measured: with `fill_method='ffil'` and a NaN open at bar 600, `g[600] == base[640]`. GapmMeasured.md:115 documents this behaviour as intended.
  - Fix: map ffill/pad → ffill and bfill/backfill → bfill, raise `ValueError` on anything else, and add a test for a typo.
- **MINOR — a0d6b58 subject; GapmMeasured.md:3, :124** — Gate A is reported as cleared, but it was checked against the owner's formula, not against a source. The Kaufman TASC article was "cited from recollection … NOT checked".
  - Fix: qualify it as "A vs owner's spec (source unchecked)", or check the article and cite it.
- **MINOR — docs/MLCompanionContract.md:27** — The tags at d7fd91d count 569 / 50 ORD, but the contract said 568 / 49. One ORD column went untallied before this port, and the changelog never names it.
  - Fix: find the column with `git log -S` and add a changelog step "568 → 569 / 49 → 50 ORD: <col> from <port>; 569 → 570 on gapm".
- **MINOR — README.md:146, docs/IndicatorDictionary.md:98** — `gapm` is already in `Category`, so `df.ta.strategy()` emits `GAPM_40_20` before Gate E has run. The consumer-facing docs give no "Gate E pending" warning.
  - Fix: add that marker to the dictionary row, or add a README note listing the pending ports.
- **NIT — GapmMeasured.md:76-77, :92-94** — Missing blank line before a heading. The float-residue paragraph sits under the wrong section (the claim itself holds: 161 exact zeros, 0 tiny residues).
  - Fix: add the blank line and move the paragraph under "The zero-denominator rule".
- **NIT — tests/test_gapm.py:168-171** — The mutants only shift the gap read and the up-sum. None shifts the dn side or the output, i.e. the back-dated-write mutant that Gate B describes.
  - Fix: add a `gapm.shift(-1)` mutant and assert it is caught.

## Outside these commits
- `tests/test_wiring_accessors.py` mutates `Category` and leaves it changed (it drops long_run / short_run / td_seq). If it runs before `tests/test_readme_counts.py`, 3 README tests fail. The full suite passes only because files run alphabetically. This is likely the known [strategy() mutates Category] bug.

## Summary

The maths is correct, and the docstring numbers that can be re-run all check out. The causal probe found 0 leaks. Scale error is about 1.7e-14 with matching NaN masks. The NaN-rate and tail values are exact, and all five wiring points are present. Gate F reproduces with the same 2 baseline failures. What fails is the evidence for the decision that mattered: the indicator screened EQUIVALENT (0.9054) and was ported on a rebuttal measurement that only ever existed in a scratchpad. Commit the screening scripts, tighten `fill_method`, qualify Gate A, and this passes.

Not checked: Kaufman source, Gate E / real-data frames (not on this machine), full suite on pandas 3.
