# Task log — TF-MEDIAN-ABSDIFF-20 (issue #118)

## Implementation summary

Ported TSFEL's `median_abs_diff` (`median(|diff(x)|)`) applied as a 20-bar trailing median of
absolute bar-to-bar log returns, scale-free form (`x` = log(close), per issue #118). Shipped as
`pandas_ta/volatility/tf_median_absdiff_20.py`, column `MEDABSDIFF_20`, category `volatility`.
Wired at all five touch points (module, `pandas_ta/volatility/__init__.py` export, `Category`
dict in `pandas_ta/__init__.py`, `core.py` accessor, `tests/test_tf_median_absdiff_20.py`).
Bumped the indicator counts in `README.md` (237→238 / 245→246 / volatility 20→21), regenerated
`docs/IndicatorDictionary.md`, bumped `docs/MLCompanionContract.md`'s tagged-column headline
(570→571 total / 216→217 `SF`), and bumped the pinned `CATEGORY_TOTAL`/`CATEGORY_BUCKETS` in
`tests/test_altport2_ports.py` (237→238, volatility 20→21). Wrote
`docs/TfMedianAbsdiff20Measured.md` (the gate receipt) and `docs/measure_tf_median_absdiff_20.py`
(environment stamp, Gate C/D synthetic numbers, plus a non-shipped comparison block added during
review round 1).

**Design decision made during the build, not just at the end:** the prototype computes the
log-return as `log(close).diff()`; the port computes `log(close / close.shift(1))` instead.
Mathematically identical, but measured to differ under Gate D's ×8/×64 bit-identity requirement —
the two-log-and-subtract form left a few-ulp residual (8.882e-16 at ×8, 1.776e-15 at ×64), the
single-log-of-a-ratio form is exact. Caught by actually running the ×8 scale test during
development, not by inspection.

Gates A, B, D cleared; C is synthetic-only (real-data counts owed to the Gate E run); E is
pending, to be run and recorded by the issue-solver launcher after this session, per this
session's explicit instructions. Full details and the measured numbers are in
`docs/TfMedianAbsdiff20Measured.md`.

Full suite at hand-off: `3 failed, 3272 passed, 83 skipped`. All three failures are pre-existing
or an expected, documented consequence of Gate E being pending (not caused by this port):
`test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` (CLAUDE.md's known break),
`test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows` (needs a sibling
checkout not present here; CI deselects it by name), and
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (expected:
`tf_median_absdiff_20` has no ledger row yet because Gate E hasn't run).

**Disclosed, not fixed (out of scope):** while running tests in a non-default file order to
investigate the pinned category-count test, found that `pandas_ta.core.AnalysisIndicators.strategy()`
mutates the live `Category[name]` list in place (`_indicators_by_category` returns the dict's own
list object; `strategy()` then calls `.remove()` on it directly with no restore). A category
sweep permanently drops its own excluded members from `Category` for the rest of the process.
Pre-existing on `dev`, unrelated to this port, and does not affect the default alphabetical
full-suite run (confirmed clean). Recorded in `docs/TfMedianAbsdiff20Measured.md`'s Gate F section.

## Review rounds (verbatim)

### Round 1 — PASS

```
VERDICT: PASS
FINDINGS:
  - severity: MINOR
    location: docs/TfMedianAbsdiff20Measured.md, Gate D row ("measured 8.88e-16 residual before the fix, 0 after — see `docs/measure_tf_median_absdiff_20.py`'s git history / this session's working notes"); repeated verbatim in docs/reviews/auto-2026-10-30-tf-median-absdiff-20/00-manifest.md's second ASSUMPTION
    problem:  The specific number 8.88e-16 (the residual of the *rejected* `log(close).diff()` form under x8/x64) is cited to "`docs/measure_tf_median_absdiff_20.py`'s git history," but that file is untracked and has zero git history (`git log --all -- docs/measure_tf_median_absdiff_20.py` returns nothing; `git status` shows it as `??`, never committed). The fallback citation, "this session's working notes," is not among the files handed to review and cannot be checked either. This is the exact failure shape CLAUDE.md names as the project's dominant defect — a specific count asserted without a traceable run — even though it concerns a discarded formula, not the shipped one.
    fix:      Either (a) re-run the comparison for `log(close).diff()` under x8/x64 and paste the actual output into the doc/script as a committed, inspectable artifact (a code comment or a `## rejected form` block in `docs/measure_tf_median_absdiff_20.py` that reproduces the 8.88e-16 number on demand), or (b) if that run can't be reproduced, strike the specific figure and write "observed during development, not preserved — not required for Gate D since the shipped form's own ×8/×64 bit-identity is what's measured below," so no unverifiable count stands as a claim.
SUMMARY: This is the cleanest-sounding port of the eighteen CLAUDE.md complains about — every number I could independently reproduce, I did reproduce, exactly: the 14-test suite passes outright; the mutant leak counts are hard pytest equalities (not docstring assertions) and I confirmed 0/31 real, 31/31 for the 10-bar mutant, 17/31 for the disclosed 1-bar escape; `docs/measure_tf_median_absdiff_20.py` run live gives bit-identical ×8/×64 and 2.186e-16/2.220e-16 at ×10/×3.7, matching the doc's "within 2.2e-16" to the ulp; all five wiring touch points name the function and column identically and `df.ta.tf_median_absdiff_20()` actually works; the README's 238/246/volatility-21 counts are independently asserted by `test_readme_counts.py` (passed) rather than hand-typed; the full suite reproduces the claimed "3 failed, 3272 passed, 83 skipped" with the exact three names, and the new `test_gate_e_ledger.py` failure is, when inspected, precisely `['tf_median_absdiff_20']` missing its row — exactly as described; the disclosed `strategy()` list-mutation bug is real, located exactly where the manifest says (`core.py:453` and `:690-692`), untouched by this session's diff, and I reproduced its claimed "238 → 235" collapse to the digit; no Gate E number is ever claimed as obtained, only the prototype's 0.7422 clearly marked as not-this-module. The one blemish is a citation to a git history that doesn't exist for a secondary, non-shipped-formula number — sloppy, worth a fix, but it indicts a footnote, not the port.
```

**Fixes applied (even though MINOR and PASS does not require it):** added a non-shipped
comparison block to `docs/measure_tf_median_absdiff_20.py` computing the rejected
`log(close).diff()` form and printing its ×8/×64 residual; ran it (`8.882e-16` at ×8, `1.776e-15`
at ×64 — the ×64 figure was not previously stated at all); replaced the unverifiable git-history
citation in both `docs/TfMedianAbsdiff20Measured.md` and `00-manifest.md` with the actual,
reproducible numbers and a pointer to the script block that regenerates them.

## Outcome

PASS at round 1 of 3 (within the cap). The one MINOR finding was fixed anyway, since it was cheap
and the project's own named failure mode is exactly "an unverifiable specific number." Task marked
done.
