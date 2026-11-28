# TTR-TDI-20 (issue #148)

## Implementation

Ported R TTR's Trend Detection Index (GPL-2.0), scale-free form, as `tdi` in
`pandas_ta/trend/`. Written from the issue's own distilled formula
(`|sum_n mom| - (sum_2n |mom| - sum_n |mom|)`, `mom = price - price[n]`), never from
`TDI.R` and never from the prototype (`docs/issues/screen/ind_screen_r5.py`'s
`ttr_tdi_20`): the prototype's `mom.fillna(0)` is a screening-harness convenience not
present in the issue's text, so it is deliberately NOT reproduced -- `mom` stays NaN
until real history exists, lengthening the warm-up to `length + multiple * length - 1`
(59 bars at the defaults) versus the prototype's shorter one. This divergence is named
explicitly in the module docstring, the test module docstring, and
`docs/TdiMeasured.md`.

Column `TDI_20_2` (length, multiple both always appended, matching the issue's own
"(Pee; 20, multiple 2)"). Category `trend` (R TTR classifies TDI as a trend indicator;
sits next to `vhf`/`chop`/`adx`, all trend-vs-chop ratio indicators in this fork).

Wiring (all five touch points): `pandas_ta/trend/tdi.py`, `pandas_ta/trend/__init__.py`,
`Category["trend"]` in `pandas_ta/__init__.py`, `AnalysisIndicators.tdi` in
`pandas_ta/core.py`, `tests/test_tdi.py`.

Docs: `docs/TdiMeasured.md` (receipt, Gate E marked pending at write time), `docs/measure_tdi.py`
(every number in the receipt and both docstrings), `docs/measure_tdi_cpu.py`. Counts
updated: `tests/test_altport2_ports.py` `CATEGORY_TOTAL` 379 -> 380, `CATEGORY_BUCKETS`
trend 65 -> 66, `docs/MLCompanionContract.md` 724 -> 725 tagged / 358 -> 359 `SF`,
`docs/IndicatorDictionary.md` regenerated (`python docs/gen_indicator_dictionary.py`),
`README.md` headline counts (379 -> 380 / 387 -> 388) and the `trend` category list.

Gate E and the ledger row are explicitly out of scope this session (launcher runs Gate
E; a receipt session records the row later) -- per the session's override rules, not
the issue's own text.

## Verification run before gate

```
python -m pytest -q tests/test_tdi.py tests/test_readme_counts.py tests/test_altport2_ports.py \
  tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py \
  tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```
Result: 1 failed, 1534 passed, 7 skipped. The one failure is
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` ("no Gate E
ledger row for ['tdi']") -- expected, not a finding.

`python docs/measure_tdi_cpu.py disable pytest` (CPU kernels without
AVX512F/AVX512_SKX/AVX2/FMA3): 116 of 116 `test_tdi.py` tests pass.

## Review round 1

VERDICT: REVISE

FINDINGS:
  - severity: CRITICAL
    location: tests/test_tdi.py:254 and docs/MLCompanionContract.md (the new #148
      census clause)
    problem: both files cited a "measured" float `3.553e-15` that was mislabelled for
      the claim it was attached to. `docs/MLCompanionContract.md` cited it as the
      overall Gate D tolerance bound, but the live `python docs/measure_tdi.py D` run
      showed the true max is `4.066e-15` (`coarse` frame, factor `0.1`) -- the stated
      bound was factually false. `tests/test_tdi.py`'s Gate A test cited it but no
      section of `docs/measure_tdi.py` had ever computed anything on the test module's
      own 400-bar frames -- the number belonged to a different gate/frame entirely,
      never measured for what it was claimed to support.
    fix: add a dedicated `docs/measure_tdi.py` section (`A1T`) that actually runs
      Gate A's oracle comparison on the test module's own 400-bar frames and quote
      that real number; fix `docs/MLCompanionContract.md`'s Gate D figure to the true
      measured `4.066e-15`.
  - severity: MAJOR
    location: pandas_ta/trend/tdi.py (module docstring)
    problem: the deliberate divergence from the issue's prototype (not reproducing its
      `mom.fillna(0)`) was disclosed in `docs/TdiMeasured.md` but never named in the
      module docstring itself -- the one place a downstream engineer calling
      `help(ta.tdi)` would actually see it.
    fix: add a paragraph next to the `Source:` line naming the prototype file and its
      `.fillna(0)` explicitly, plus the consequence (59-bar vs. the prototype's shorter
      warm-up).

SUMMARY: the arithmetic, wiring, mutants and level-shift reasoning all checked out
against a live run; the two findings were both instances of the repo's documented
dominant defect -- a claim written before (or copied from a different place than) it
was measured.

Fix applied:
- `docs/measure_tdi.py`: added section `A1T`, a genuine 400-bar Gate A oracle
  comparison (same builders/seeds as `tests/test_tdi.py`), not a hardcoded print.
  Live max: `jump`, `3.553e-15`.
- `tests/test_tdi.py`: Gate A test docstring now cites `3.553e-15` sourced from
  `A1T`; module docstring distinguishes the 1,500-bar `§A1` bound (`3.109e-15`) from
  the 400-bar `§A1T` bound and explains why they differ; item 1 now names the
  prototype file and its `.fillna(0)` explicitly rather than saying "no fillna".
- `docs/MLCompanionContract.md`: Gate D figure corrected `3.553e-15` -> `4.066e-15`.
- `pandas_ta/trend/tdi.py`: new paragraph after `Source:` naming the prototype file,
  its `.fillna(0)`, and the warm-up consequence.

Re-verified after the fix: `python docs/measure_tdi.py A1 A1T D` live output matches
every cited number; targeted suite re-run clean (1 expected failure, 1534 passed, 7
skipped); CPU-kernel variant re-run clean (116/116).

## Review round 2

VERDICT: PASS

FINDINGS: two NIT only --
  1. the 400-bar `§A1T` figure (`3.553e-15`, on `jump`) happens to numerically equal
     `§D`'s x10-on-`jump` figure -- a real coincidence of this run (confirmed by
     checking both computation paths independently), not a leftover copy, but worth a
     footnote so a future skim-reviewer doesn't "fix" it back to the wrong citation.
  2. `section_A1T()` didn't name which frame produced the printed max; a reader had to
     scan the table by hand.

SUMMARY: both round-1 fixes verified genuine -- `§A1T` is a real, separate 400-bar
computation whose live max matches every citation; `docs/MLCompanionContract.md`'s
corrected Gate D figure matches `docs/measure_tdi.py D`'s live output and
`docs/TdiMeasured.md`'s own (untouched, already-correct) figure; a full-text sweep for
all three disputed figures across the repo found no stray mislabelled occurrence;
`pandas_ta/trend/tdi.py`'s docstring now names the prototype and its `.fillna(0)`
explicitly, understandable without `docs/TdiMeasured.md`. Full pytest sweep reproduces
exactly "1 failed, 1534 passed, 7 skipped" with the one failure confirmed to be the
expected Gate E ledger gap; `git status`/diff-stat confirmed the edit touched only the
already-reviewed file set. Gate clears.

Both NITs applied: `section_A1T()` now prints a `worst: <frame> <value>` line and a
coincidence footnote; `tests/test_tdi.py`'s module docstring carries the same
footnote. Re-verified: `python docs/measure_tdi.py A1T` and the targeted suite both
re-run clean after the NIT edits (1 failed, 1534 passed, 7 skipped).

## Closing note

Commit a2989a7 (after this file was written) recorded the launcher's Gate E run:
`is148-tdi-c25dda7f`, SHIP, max |rho| 0.4924 vs `mad_pct_Pctl` (per-frame max median
0.4915), in `docs/gate_e_ledger.csv`. The "1 failed (expected: no ledger row)" result
above is from before that row existed; `test_every_indicator_that_needs_a_row_has_one`
now passes.
