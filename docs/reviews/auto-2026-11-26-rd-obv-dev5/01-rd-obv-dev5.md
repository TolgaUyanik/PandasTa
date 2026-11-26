# Task 01 — RD-OBV-DEV5 (issue #177)

## Implementation summary

Ported `rd_obv_dev5` (volume category): `(OBV - SMA(OBV, 5)) / SMA(volume, 20)`, per issue #177's
"What" line and its own scale-free parenthetical. Reused the fork's already-tested `obv()` and
`sma()`. Shipped only the OBV-vs-its-SMA half of the poster's two-part ADX+OBV condition, with that
scoping stated in the module docstring and `docs/RdObvDev5Measured.md` (the ADX>40 half is the
fork's existing `pandas_ta.trend.adx`; combining the two is a strategy decision, not a feature
column).

Files: `pandas_ta/volume/rd_obv_dev5.py` (new), `tests/test_rd_obv_dev5.py` (new, 17 tests),
`docs/measure_rd_obv_dev5.py` / `docs/measure_rd_obv_dev5_cpu.py` (new), `docs/RdObvDev5Measured.md`
(new). Wiring: `pandas_ta/volume/__init__.py`, `pandas_ta/__init__.py` (`Category["volume"]`),
`pandas_ta/core.py` (accessor), `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 412→413,
`CATEGORY_BUCKETS["volume"]` 47→48), `README.md` (413/421 headline, `volume (48)` row),
`docs/MLCompanionContract.md` (757→758 tally, 383→384 `SF`), `docs/IndicatorDictionary.md`
(regenerated).

Gates A-D measured (see `docs/RdObvDev5Measured.md` for full numbers): Gate A correctness 681/681
bars matching an independent recompute (max|diff| 6.16e-15); Gate B mutant leaks 9/9 vs. real
module's 0/9; Gate D price-only rescale bit-identical at x8/x64/x10/x3.7 (OBV reads only
`sign(close.diff())`), volume-only rescale bit-identical at x8/x64, within 1e-9 at x10/x3.7.
CPU-variant re-run (`NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`): 17/17 pass. Gate E:
pending, launcher's job.

Verification run: `python -m pytest -q tests/test_rd_obv_dev5.py tests/test_readme_counts.py
tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
— 1,699 passed, 7 skipped, 1 failed (expected: `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
owed to the launcher's Gate E run).

## Review — round 1

VERDICT: PASS
FINDINGS:
  - severity: NIT
    location: pandas_ta/volume/rd_obv_dev5.py:93-136 vs docs/RdObvDev5Measured.md
    problem: No functional, arithmetic, wiring, or scope defect found anywhere in the diff. Gate A's formula is the issue's literal `(OBV - SMA5(OBV)) / SMA20(volume)`, with `obv()` reused unmodified and the two SMAs taken via the fork's own `sma()`. The "5" is attributed to the poster's words, the "20" to the issue's own parenthetical, and the ADX>40 half is explicitly disclosed as dropped rather than silently discarded. The mutant in `tests/test_rd_obv_dev5.py::_load_mutant` targets a real look-ahead class (`.shift(-1)` on the OBV series feeding both SMAs), is asserted unique in source (`src.count(old) == 1`), is proven live against the real module, and leaks 9/9 against the real module's 0/9 — matching `RdObvDev5Measured.md`'s Gate B row exactly. The scale-free claim is true against `obv.py`'s actual implementation (`signed_series` uses `series.diff(1)`'s sign, invariant to any positive price scale; `sma()` is a plain linear `rolling().mean()`), and is tested at k=10/3.7 in addition to 8/64, with the correct bit-identical-vs-tolerance split (price: all four bit-identical; volume: 8/64 bit-identical, 10/3.7 within 1e-9). Every number in the Measured.md traces to the code: 19-bar warm-up (`max(5,20)-1`), 681 = 700-19, 881 = 900-19, 17 total tests (counted and matched against the file), OFFSETS = 9. Wiring is consistent end-to-end: `core.py`'s accessor forwards `vol_length`, the column name `RD_OBV_DEV5_{length}_{vol_length}` matches module/test/accessor, and every count bump (412→413, 47/48 Category bucket, 757→758, 383→384, README 412/420→413/421) lands in exactly the files the task allowed and nowhere else (`git diff --name-status` and untracked list match the allowed set 1:1). `docs/measure_rd_obv_dev5_cpu.py` sets `NPY_DISABLE_CPU_FEATURES` before the `numpy` import and asserts the four named features are actually off before running. No helper module (`obv.py`, `sma.py`) was touched.
    fix: None required. If anything, tighten going forward: the independent-recompute test reuses the module's own `obv()` import rather than a second independent OBV implementation — acceptable here only because the task and docstring explicitly scope "independent" to mean "not calling the module's own `sma()`," and `obv()` is cited as separately already-tested; keep flagging this distinction explicitly in future ports rather than letting "independent" quietly broaden.
SUMMARY: This is a clean, rule-compliant port — the formula, the mutant, the scale-free proofs, the measured numbers, and every count bump cross-check against the code and against each other without a single invented digit or silent scope change; the poster's two-part condition is honestly cut down to one half with that cut stated, not hidden. Nothing here earns applause, it earns nothing more than not having to be sent back — which is the bar. Ship it.

## Outcome

PASS on round 1. No fixes applied (NIT only, no action required). Task done.
