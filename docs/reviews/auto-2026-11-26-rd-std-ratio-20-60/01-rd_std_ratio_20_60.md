# Task: rd_std_ratio_20_60 port (issue #179)

## Implementation summary

- `pandas_ta/volatility/rd_std_ratio_20_60.py` — new module. `RD_STD_RATIO_20_60_{length}_{avg_length}`
  = `stdev(close, length) / sma(stdev(close, length), avg_length)`, defaults `length=20,
  avg_length=60` (the issue's own `p=20` / `3p=60`). Division by a zero average stdev → NaN.
- `tests/test_rd_std_ratio_20_60.py` — 20 tests: Gate A (independent sliding-window oracle +
  hand-derived fixture), Gate B (future-splice sweep + look-ahead mutant), Gate D (x8/x64
  bit-identical, x10/x3.7 tolerance), Gate C (reachability), wiring.
- `docs/measure_rd_std_ratio_20_60.py`, `docs/measure_rd_std_ratio_20_60_cpu.py` — receipt
  reproduction scripts (the latter under `NPY_DISABLE_CPU_FEATURES`).
- `docs/RdStdRatio2060Measured.md` — the receipt. Gate E marked pending (launcher runs it).
- Wiring: `pandas_ta/volatility/__init__.py`, `pandas_ta/__init__.py` (`Category`),
  `pandas_ta/core.py` (accessor).
- Count bumps: `README.md` (413→414 / 421→422 / volatility 42→43), `tests/test_altport2_ports.py`
  (`CATEGORY_TOTAL` 413→414, `CATEGORY_BUCKETS["volatility"]` 42→43),
  `docs/MLCompanionContract.md` (758→759 tagged, 384→385 `SF`), `docs/IndicatorDictionary.md`
  regenerated.

## Review round 1

**VERDICT: PASS**

```
FINDINGS:
  - severity: MINOR
    location: pandas_ta/volatility/rd_std_ratio_20_60.py:53-73 (SCALE-FREE section), docs/RdStdRatio2060Measured.md Gate D section
    problem:  The scale-free argument builds a power-of-two exactness argument on pandas'
      rolling .var() without naming or ruling out the catastrophic-cancellation failure mode
      this fork already documents for a different stdev-based module (avwap_z): computing
      variance via E[X^2]-E[X]^2 loses precision when true variance is small relative to
      price^2. The module here is actually safe (variance.py uses a deviation-from-mean
      reduction, not that naive form; verified against the actual test run), but the
      docstring didn't say so.
    fix:      Add one sentence to the SCALE-FREE paragraph naming the avwap_z precedent and
      stating explicitly that variance.py uses close.rolling(...).var(ddof) (deviation-first),
      which is why the documented cancellation risk does not apply here.
SUMMARY: Every load-bearing claim (Gate A hand-derived + oracle, Gate B future-splice sweep +
  mutant, Gate D x8/x64/x10/x3.7 numbers, wiring, count bumps, pytest pass/fail counts) was
  independently reproduced by the reviewer and matched the receipt exactly. Scope clean, no
  files touched outside the port. One documentation-completeness nit, not a correctness defect.
```

## Fix applied

Added the named sentence to both `pandas_ta/volatility/rd_std_ratio_20_60.py`'s SCALE-FREE
section and `docs/RdStdRatio2060Measured.md`'s Gate D section. Re-ran the full named gate test
set after the edit: same result, 1,710 passed / 7 skipped / 1 expected failure
(`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`).

**Status: DONE** (round 1, no further REVISE needed).
