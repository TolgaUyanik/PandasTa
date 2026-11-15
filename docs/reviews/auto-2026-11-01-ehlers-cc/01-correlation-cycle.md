# Task: port Correlation Cycle (issue #30) through Gates A-D

## Implementation summary

- `pandas_ta/cycles/correlation_cycle.py`: `CC_REAL_<length>`, `CC_IMAG_<length>`,
  `CC_ANGLE_<length>`. Real/Imag are Pearson correlations of `close` against a cosine / sine
  reference wave of one fixed period (`length`, default 20), reusing the same closed-form sums
  already shipped and tested in `pandas_ta/overlap/linreg.py`'s `r=True` branch. Angle is
  `degrees(atan2(Imag, Real))`.
- Wired at all 5 touch points: module, `pandas_ta/cycles/__init__.py` export, `Category["cycles"]`
  in `pandas_ta/__init__.py`, `df.ta.correlation_cycle()` accessor in `pandas_ta/core.py`,
  `tests/test_correlation_cycle.py`.
- `docs/CorrelationCycleMeasured.md`: Gates A/B/D measured, Gate C synthetic-only, Gate E marked
  PENDING (run by issue-solver after this session).
- `docs/EhlersDspMeasured.md`: family screening table, all other issue #30 candidates DEFERRED
  with reasons (not attempted this session — file-budget and recursive-filter risk).
- Doc-count fixups: `README.md`, `docs/IndicatorDictionary.md` (regenerated),
  `docs/MLCompanionContract.md` (SF count), `tests/test_altport2_ports.py`
  (`CATEGORY_TOTAL`).

## Review round 1

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: docs/EhlersDspMeasured.md:17 (table row "Correlation Cycle (angle + market state)")
    problem:  Verdict cell read "SHIPPED (partial: angle only)" -- false, contradicts the same
      file's own intro paragraph and docs/CorrelationCycleMeasured.md: Real and Imag are the
      primary outputs and shipped too, not just Angle.
    fix:      Change the cell to "SHIPPED (Real/Imag/Angle; market state skipped)".
  - severity: MINOR
    location: tests/test_correlation_cycle.py:71-85
    problem:  Warm-up NaN assertion only checked CC_REAL, not CC_IMAG, in both closed-form tests.
    fix:      Add the matching CC_IMAG warm-up-NaN assertion to both tests.
  - severity: NIT
    location: tests/test_correlation_cycle.py:131-136
    problem:  _REAL_BLOCK assigned but never read.
    fix:      Wire it in or delete it.
  - severity: NIT
    location: tests/test_correlation_cycle.py:107
    problem:  Stray f-string prefixes with no interpolation.
    fix:      Drop the f prefixes.
  - severity: NIT
    location: pandas_ta/cycles/correlation_cycle.py:39-40
    problem:  Inconsistent float(...) casting between cos_sum/sin_sum and cos2_sum/sin2_sum.
    fix:      Cast all four consistently.
SUMMARY: The arithmetic holds up under independent re-derivation and the causality/scale-free
harnesses have no blind spot, but the family screening ledger -- the one document whose job is
to stop a false claim from outliving its session -- shipped with exactly that: a verdict cell
claiming only Angle shipped when Real and Imag shipped too, contradicting the correct sentence
seven lines above it in the same file. Fix that line before this goes near a launcher that will
trust it.
```

Fixes applied: EhlersDspMeasured.md cell corrected; both closed-form tests now assert CC_IMAG
warm-up NaNs; `_REAL_BLOCK` deleted (unused, and each mutant's own `assert src.count(old)==1`
already proves presence/uniqueness individually); f-string prefixes dropped; `cos_sum`/`sin_sum`
now `float(...)`-cast to match `cos2_sum`/`sin2_sum`. `tests/test_correlation_cycle.py` re-run:
14 passed.

## Review round 2

```
VERDICT: PASS
FINDINGS:
  - severity: NIT
    location: docs/CorrelationCycleMeasured.md:10 and EhlersDspMeasured.md table row
    problem:  The row label still carries the parenthetical "(angle + market state)" quoted
      verbatim from the issue's table; a reader skimming only the label column could misread it
      as a claim rather than a quotation.
    fix:      Optional: parenthesize as "(issue's label: angle + market state)". Not owed before
      merge -- the adjacent verdict cell and body text already disambiguate.
SUMMARY: Both round-1 fixes verified byte-for-byte... [full text in the task notification;
no further action required]. Scope clean: exactly one new pandas_ta/<category>/*.py file, no
forbidden files touched, Gate E correctly marked PENDING everywhere, every number in the
measured doc reproduces live. Nothing here earns a revert.
```

No further fix applied (round-2 finding is explicitly optional/NIT, not owed before merge).

## Full suite, post-fix

`python -m pytest -q`: 3 failed, 3865 passed, 83 skipped. The 3 failures are:
`test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows` (pre-existing,
needs `../AlternativeRepos` checkout), `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
(pre-existing, documented in CLAUDE.md "Known breaks"), and
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (expected: "no Gate E
ledger row for ['correlation_cycle']" -- Gate E is run by the launcher after this session).
