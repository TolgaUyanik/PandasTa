# Task: c22-entropy-pairs (issue #133)

## Round 1

VERDICT: REVISE

FINDINGS (verbatim):
- severity: MAJOR
  location: pandas_ta/statistics/c22_entropy_pairs.py:159-160 (docstring title line wrap) -> docs/IndicatorDictionary.md:236
  problem: the docstring's title wrapped onto two physical lines
    ("... alphabet" / "(C22ENTROPYPAIRS)"), so `docs/gen_indicator_
    dictionary.py`'s naive title/body parser (lines[0] = title, then the
    next contiguous non-blank run = body) swallowed the parenthetical short
    name as the entire body and never reached the real description. The
    shipped `docs/IndicatorDictionary.md:236` row was empty of content.
  fix: put title + short name on one line, like every sibling port, and
    regenerate the dictionary.
- severity: MAJOR
  location: pandas_ta/statistics/c22_entropy_pairs.py:108; tests/test_c22_entropy_pairs.py
  problem: the `length` guard-band fallback branch (sub-floor, zero, falsy,
    or non-default length -> default-100 column under the matching column
    NAME) had zero test coverage, despite the sibling port (`c22_ami2`)
    pinning exactly this branch, and CLAUDE.md calling column naming "API".
  fix: add a parametrized length-guard-band test mirroring `c22_ami2`'s,
    checking both `.name` and the fired-bar count at several lengths
    including sub-floor ones.
- severity: MINOR
  location: pandas_ta/statistics/c22_entropy_pairs.py:225-233 (Causal / Scale-free paragraphs)
  problem: unlike `c22_ami2.py`, these paragraphs deferred every
    quantitative claim to the receipt instead of inlining the headline
    figures.
  fix: inline the headline tie-rate / bars-moved figures from the receipt.

SUMMARY (verbatim): The algorithm itself is clean -- the letter rule,
quantile convention disclosure, entropy formula, exact-rational oracle, and
mutant/causality sweep are all faithful to the sibling port's bar and
nothing here fabricates a number the receipt doesn't back (the
1390-passed/1-expected-failed claim reproduced bit for bit on this machine,
under both dispatch settings). But two concrete things are actually broken
in what got committed: the generated `docs/IndicatorDictionary.md` row for
this column is empty of content because the docstring's title wraps onto
two lines and silently defeats the generator's naive parser, and the
`length`-floor fallback branch -- a real, user-reachable code path that
changes the column's OWN NAME -- has zero test coverage despite the sibling
port pinning exactly this branch. Both are mechanical, narrowly-scoped
fixes, not a redesign, but "92 passing tests" oversold a port that ships one
dead documentation row and one untested branch; fix both before this goes
to Gate E.

## Fixes applied (round 1)

1. Merged the docstring's title onto one physical line
   (`pandas_ta/statistics/c22_entropy_pairs.py`); regenerated
   `docs/IndicatorDictionary.md` — row 236 now carries a real description.
2. Added 18 tests to `tests/test_c22_entropy_pairs.py`: the length
   guard-band / naming test (parametrized at `None, 0, 1, MIN_LENGTH - 1,
   MIN_LENGTH, 250, 250.7`), a short-input probe, the five-wiring-touch-
   points check, the accessor-forwards-parameters check, offset/fillna, the
   chunk-budget invariance, and a stricter dictionary-row test that would
   have caught finding #1 directly (checks for descriptive words and
   explicitly rejects the leaked `(C22ENTROPYPAIRS)` parenthetical).
3. Inlined the receipt's headline Causal/Scale-free figures into the
   module docstring (MINOR, fixed opportunistically).
4. Updated `docs/C22EntropyPairsMeasured.md` test counts (92 -> 110 for the
   module, 1390 -> 1408 for the required subset) and reran every
   verification command.

Verification after fixes:
`python -m pytest -q tests/test_c22_entropy_pairs.py` -> 110 passed.
`python -m pytest -q tests/test_c22_entropy_pairs.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
-> 1408 passed, 7 skipped, 1 failed (expected: `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`).
`python docs/measure_c22_entropy_pairs_cpu.py` (AVX512F/AVX512_SKX/AVX2/FMA3
disabled) -> 110 passed.

Committed as a follow-up commit; re-dispatching the Fletcher reviewer for
round 2.
