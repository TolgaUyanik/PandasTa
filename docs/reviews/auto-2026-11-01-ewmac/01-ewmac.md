# Task: EWMAC port (issue #29)

## Implementation summary

- `pandas_ta/momentum/ewmac.py`: `ewmac(close, vol_length=None, offset=None, **kwargs)`,
  returns a 6-column `DataFrame` (`EWMAC_<fast>_<slow>_<vol_length>` for Carver's six
  pairs). `sigma = close.diff().ewm(span=vol_length, adjust=False).std()`, computed once
  and shared across all six columns. Raw ratio only — no forecast scalar, no cap.
- Wired: `pandas_ta/momentum/__init__.py` (export), `pandas_ta/__init__.py` (`Category`),
  `pandas_ta/core.py` (`df.ta.ewmac()` accessor), `tests/test_ewmac.py` (13 tests).
- Docs: `docs/EwmacMeasured.md` (new), `docs/measure_ewmac.py` (new, produces the numbers
  quoted in the Measured doc), `README.md` / `docs/IndicatorDictionary.md` /
  `docs/MLCompanionContract.md` (counts updated: momentum 60→61, Category 263→264,
  accessor surface 271→272, dictionary-probe 265→266, SF tag count 245→251),
  `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 263→264, one line).

## Review round 1

Dispatched a Fletcher reviewer (`Explore` subagent, read-only) against the full diff plus
the original user ask. Full prompt covered: formula correctness, the two Gate A
assumptions, the Kaufman squared-stdev disclosure, the Gate B mutant test's genuineness,
the Gate D scale-free math, every number in `docs/EwmacMeasured.md` traced back to a
command actually run this session, wiring completeness, and scope discipline.

```
VERDICT: PASS
FINDINGS:
  - severity: NIT
    location: pandas_ta/core.py:1090 (`def ewmac(self, vol_length=None, offset=None, **kwargs):`)
    problem: Every other method inside the momentum block of `core.py` is in strict
      alphabetical order. `ewmac` was placed after `lrsi` and before `macd` instead of
      between `eri` and `fisher`. Cosmetic only — wiring itself is correct and tested.
    fix: Move the `ewmac` method to sit between `eri` and `fisher` in core.py.
SUMMARY: This port is clean and matches the repo's own established bar (`ie_asym`)
almost exactly in shape, rigor, and honesty. [The reviewer independently re-ran
tests/test_ewmac.py (13/13), docs/measure_ewmac.py, the full suite (3 failed/3914
passed/83 skipped matching the three named pre-existing/expected failures), and
test_readme_counts.py / test_ml_companions.py, and every number checked out exactly.]
The lone finding is a cosmetic alphabetical-ordering slip in core.py with zero
functional consequence.
```

## Fix applied

Moved the `ewmac` accessor method in `pandas_ta/core.py` to sit between `eri` and
`fisher`, matching the alphabetical placement already used by `Category` and
`pandas_ta/momentum/__init__.py`. Re-ran `tests/test_ewmac.py` +
`tests/test_wiring_accessors.py`: 80 passed. No second review round needed — the NIT was
the only finding and did not gate the PASS.

## Status: PASS, round 1. No escalation.
