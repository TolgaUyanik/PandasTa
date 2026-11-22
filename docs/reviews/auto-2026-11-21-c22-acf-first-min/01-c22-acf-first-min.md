# C22-ACF-FIRST-MIN — gate log

## Round 1

VERDICT: REVISE

FINDINGS:
- severity: MAJOR
  location: docs/C22AcfFirstMinMeasured.md:16
  problem: Gate D headline row claimed "0 of 467-to-1,400 bars moved under
    x10" — "467" is a copy-paste leak from the sibling
    C22PeriodicityMeasured.md / c22_ami2 receipts' own windows-per-frame
    convention, not a number this port's harness ever produced (its own
    §D2 table, and a live re-run of `python docs/measure_c22_acf_first_min.py D`,
    both show 0 moved over 1,400 fired bars on all six frames).
  fix: Change the headline row to "0 of 1,400 bars moved under x10 on each
    of six frames" and sweep the rest of the receipt for any other number
    not traceable to this session's own measured output.

SUMMARY: Port itself verified solid by the reviewer (independently
re-ran Gate A's section P black-box check against pycatch22 live: 0/8,400
disagree; confirmed the mutant is a genuine unique write-index back-date,
caught every time; confirmed Gate D's bit-identical claim given the
pure-ratio implementation; confirmed all five wiring touch points;
confirmed the named test subset reproduces 175 passed / 7 skipped with the
Gate E ledger failing exactly as expected on `['c22_acf_first_min']`). One
MAJOR: an unmeasured "467" copy-pasted from a different indicator's
receipt in the Gate D summary row.

### Fix applied

`docs/C22AcfFirstMinMeasured.md`'s Gate D summary row changed to
"×8/×64 bit-identical; 0 of 1,400 bars moved under ×10 on each of six
frames; `0 < fires < n`; not constant on five of six frames — §D", matching
§D2's own table and a fresh run of `python docs/measure_c22_acf_first_min.py D`.
Grepped the new receipt, module docstring, test module and harness for any
other occurrence of "467" (the sibling receipts' own windows-per-frame
figure) — none found outside this one line.

Re-ran the required test subset after the fix:
`python -m pytest -q tests/test_c22_acf_first_min.py tests/test_readme_counts.py
tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
→ **175 passed, 7 skipped** (unchanged — a docs-only fix).

## Round 2

VERDICT: PASS

FINDINGS: (none)

SUMMARY: The round-1 MAJOR is fixed exactly as described; "467" confirmed
absent from the receipt, the module, the test module and the harness; a
fresh independent run of sections A, B, C, D, E, G reproduces every
printed number in the receipt digit for digit; the required test subset
reproduces 175 passed / 7 skipped; the five wiring diffs are internally
consistent. Clean — no further rounds needed.
