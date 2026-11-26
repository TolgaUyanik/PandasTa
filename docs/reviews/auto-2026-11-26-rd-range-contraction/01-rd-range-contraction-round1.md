# rd-range-contraction — review round 1

VERDICT: REVISE

FINDINGS:
  - severity: MAJOR
    location: pandas_ta/__init__.py (Category["volatility"]), README.md:158,
      docs/RdRangeContractionMeasured.md ("Counters touched")
    problem: `rd_range_contraction` was inserted between `pdist` and `range_compress_run`,
      which is not its alphabetical slot. Lexicographically `"rd_range_contraction"` sorts
      after both `"range_compress_run"` and `"range_profile"` (second character `d` > `a`)
      and before `"rogers_satchell"` (`d` < `o`). The auto-generated
      `docs/IndicatorDictionary.md` already placed it correctly (between `range_profile` and
      `rogers_satchell`), contradicting the hand-edited `Category` list and the receipt's own
      claim.
    fix: Move `"rd_range_contraction"` to sit between `"range_profile"` and
      `"rogers_satchell"` in `pandas_ta/__init__.py`'s `Category["volatility"]` list and in
      `README.md`'s volatility line; correct the matching import order in
      `pandas_ta/volatility/__init__.py`; fix the receipt's "Counters touched" sentence.
SUMMARY: Gate A/B/D math, the causality mutant, and the receipt's numeric claims all verified
  independently and reproduced exactly. The only defect was a wiring-ordering claim that was
  simply wrong and self-contradicted by this same commit's own correctly auto-generated
  dictionary -- fixed below.

## Fix applied

- `pandas_ta/__init__.py`: moved `"rd_range_contraction"` to between `"range_profile"` and
  `"rogers_satchell"`.
- `README.md`: same move in the volatility line.
- `pandas_ta/volatility/__init__.py`: reordered the import to sit between `range_profile`/
  `natr` and `rogers_satchell` (matching the list's existing, pre-port position of `natr`).
- `docs/RdRangeContractionMeasured.md`: corrected the "Counters touched" sentence to say
  `range_profile` / `rogers_satchell` instead of `pdist` / `range_compress_run`.
- Re-ran the required test command: 1,623 passed, 7 skipped, 1 failed (the expected
  `test_gate_e_ledger` owed row). Re-ran `python docs/gen_indicator_dictionary.py`: no diff,
  confirming the fix now matches the auto-generated dictionary.
