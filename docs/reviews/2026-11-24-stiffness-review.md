# Brutally Honest Review — stiffness (issue #259)

**Date:** 2026-11-24
**Target:** README.md, docs/IndicatorDictionary.md, docs/MLCompanionContract.md, pandas_ta/__init__.py, pandas_ta/core.py, pandas_ta/trend/__init__.py, tests/test_altport2_ports.py, docs/StiffnessMeasured.md, docs/measure_stiffness.py, pandas_ta/trend/stiffness.py, tests/test_stiffness.py
**Type:** code (plus a text receipt)
**Verdict:** REVISE

## Findings

### MAJOR
- **docs/StiffnessMeasured.md §L, last sentence ("Pre-port screening on 16 different synthetic frames read 0.7718 for the same comparator.")** — `docs/measure_stiffness.py` never prints this number. A grep of the script finds no `0.7718`, no "16 frames" and no screening section, and the receipt's exception list (pytest counts, wiring counts, asserted bounds) does not cover it. The acceptance criterion says every number in the receipt must be reproducible by that script, so this is an unbacked claim with a specific count. It is the defect class CLAUDE.md calls dominant.
  - Fix: Delete the sentence. Or add a §L2 block to `docs/measure_stiffness.py` that builds the 16 screening frames and prints the MADISP_200_SMA median |ρ|, then quote that output.

### MINOR / NIT
- **MINOR — docs/StiffnessMeasured.md §F, and its exception item 1** — Exception 1 says "§F's counts are pytest's, from the run named there". §F names no run and gives no counts, only "see the PR". The "Both repos' suites green" done-when line has no evidence in the receipt. Measured here: `tests/test_stiffness.py` 269 passed; altport2, readme_counts, wiring_accessors, ml_companions and indicator_list_tables 107 passed, 7 skipped.
  - Fix: Put the targeted run's exact pytest summary line or lines and the date in §F. Or reword exception 1 so it no longer promises counts that are not there.
- **MINOR — pandas_ta/trend/stiffness.py:121 (`def stiffness(close, offset=None, **kwargs)`)** — The issue lists `ma_length`, `std_mult` and `length` as parameters. The module hardcodes them, which is defensible under the Gate E ledger, but `**kwargs` swallows them silently. Verified: `ta.stiffness(c, length=20).name == "STIFF_60"`. A caller asking for a 20-bar window gets the 60-bar column back with no error.
  - Fix: At the top of the function, raise `TypeError` if any of `{"length", "ma_length", "std_mult"}` is in kwargs, with a message pointing to the module constants. Pin it with one test in `tests/test_stiffness.py`.
- **NIT — pandas_ta/trend/stiffness.py, comment above `sd = stdev(...)` ("§A4 measures the ddof=1 reading as a different column")** — Wrong section reference. The ddof=1 reading is measured in §A3; §A4 is the prefix-truncation test.
  - Fix: Change "§A4" to "§A3".
- **NIT — docs/StiffnessMeasured.md §Z** — The receipt gives 1.756 ms; this run printed 1.734 ms. It is labelled machine- and run-specific, so this is not a false claim, but it will never match a rerun exactly.
  - Fix: Write "~1.7 ms" or "on the order of 2 ms" instead of a 4-digit timing.

## Summary

The port itself is clean, and most of the receipt holds up. The formula matches the issue line by line: SMA(100), ddof=0 std, strict `>`, current bar included, a 60-bar count with NaN until full, first value at bar 158. A pure-Python oracle and TA-Lib each match it bit for bit on 1,342 of 1,342 bars of all 9 frames. All five wiring touch points are present, and the accessor takes `offset` only because there are no other parameters to forward. Gate B is a real mutant test: the shipped source is edited and exec'd in memory (read with `Path.read_text` rather than importlib, which is equivalent). The module is caught 0 of 36 times; the five lead mutants are caught 5 to 36 of 36 times, and the lag blind spot is honestly pinned. Gate D's x8/x64 bit-identity holds in 36 of 36 cells and x10/x3.7 moves 0 bars, with a non-affine check so the test is not vacuous. Gate C's counts match the script, and its real-data part is honestly marked owed alongside Gate E. README, `CATEGORY_TOTAL`/`CATEGORY_BUCKETS`, MLCompanionContract and the regenerated dictionary all agree on 385/393/trend 66. I reran the script and checked every number in the receipt, module docstring and test docstring against its output; all match except one: the "0.7718 on 16 screening frames" sentence, which no script prints. That breaks the explicit reproducibility criterion and is the defect class this repo's history warns about, so the verdict is REVISE until it is removed or backed by the script. Everything else is minor polish: the empty §F, silently ignored parameter kwargs, a wrong section reference and a precise timing figure.

I did not run the full suite, the Gate E ledger test (it needs `GATE_E_PENDING_OK=1`, and setting it needed approval) or Backtesting's suite. I also did not check that the dictionary regenerates byte-identical, because running the generator writes the file.
