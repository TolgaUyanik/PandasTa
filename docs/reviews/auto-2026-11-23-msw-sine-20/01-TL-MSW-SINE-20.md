# TL-MSW-SINE-20 (issue #146)

## Implementation

Ported Ehlers' MESA Sine Wave (in-phase line, `sin(phase)`), fixed-period DFT form, as
`msw_sine` in `pandas_ta/cycles/`. Written from Ehlers' published pseudocode ("MESA Sine Wave
Indicator", Stocks & Commodities, Apr 1996; Rocket Science for Traders, Wiley 2001, ch. 11), never
from Tulip Indicators' `msw.c` (LGPL-3.0, catalog attribution only) nor the issue's prototype
script. Sister port of the already-merged issue #145 (`msw_lead`, the lead line
`sin(phase + pi/4)`): identical phase arithmetic, only the final output line differs.

Scale-free guard per the issue: `|RealPart| > 0.001 * close` (not Ehlers' raw-price-unit
`0.001`, which the issue's own prototype pre-flight measured as flipping sign under a price x8
rescale).

Wiring (all five touch points): `pandas_ta/cycles/msw_sine.py`, `pandas_ta/cycles/__init__.py`,
`Category["cycles"]` in `pandas_ta/__init__.py`, `AnalysisIndicators.msw_sine` in
`pandas_ta/core.py`, `tests/test_msw_sine.py`.

Docs: `docs/MswSineMeasured.md` (receipt, Gate E marked pending), `docs/measure_msw_sine_proxy.py`,
`docs/measure_msw_sine_cpu.py`. Counts updated: `tests/test_altport2_ports.py` `CATEGORY_TOTAL`
378 -> 379, `docs/MLCompanionContract.md` 723 -> 724 tagged / 357 -> 358 `SF`,
`docs/IndicatorDictionary.md` regenerated, `README.md` headline/accessor counts and the `cycles`
category list.

Gate E and the ledger row are explicitly out of scope this session (launcher runs Gate E; a
receipt session records the row later) — per the session's override rules, not the issue's own
text.

## Verification run before gate

```
python -m pytest -q tests/test_msw_sine.py tests/test_readme_counts.py tests/test_altport2_ports.py \
  tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py \
  tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```
Result: 1 failed, 1422 passed, 7 skipped. The one failure is
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` — expected, not a finding.

`python docs/measure_msw_sine_cpu.py disable pytest` (CPU kernels without
AVX512F/AVX512_SKX/AVX2/FMA3): 12 of 12 `test_msw_sine.py` tests pass.

## Review round 1

VERDICT: REVISE

FINDINGS:
  - severity: MAJOR
    location: tests/test_msw_sine.py:27
    problem: docstring claimed the degenerate imag-shift mutant "differs on 1,178 of 1,200 bars,
      same count as msw_lead", but `python docs/measure_msw_sine_proxy.py` prints "imag-shift
      differs on 1178 of 1181 bars" (1,181 = non-NaN count after warm-up), and
      `docs/MswSineMeasured.md` already stated it correctly as "1,178 of 1,181 non-NaN bars" —
      the test docstring disagreed with both its own cited source script and the sibling doc.
    fix: change the wording to "1,178 of 1,181 non-NaN bars", re-run the proxy script to confirm.

SUMMARY: math, wiring, mutants, scale-free and CPU-kernel checks all correct; one docstring number
copy-pasted from the sister port's narrative instead of measured fresh — the repo's named
"claim written before it was measured" failure mode, caught on a brand-new file.

Fix applied: `tests/test_msw_sine.py` lines 26-30 reworded to "1,178 of 1,181 non-NaN bars",
citing `docs/measure_msw_sine_proxy.py`'s "mutant liveness" section directly.

## Review round 2

VERDICT: PASS

FINDINGS: none.

SUMMARY: fix verified correct and live (fresh `measure_msw_sine_proxy.py` run reprints the same
number), targeted suite re-run clean (1 expected failure, 1422 passed, 7 skipped), `git status`
shows only the known file set. Gate clears.
