# Brutally Honest Review — PFE / signed path efficiency task closure

**Date:** 2026-10-22
**Target:** `pandas_ta/momentum/pfe.py`, `tests/test_pfe.py`, `docs/PfeMeasured.md`, `docs/SignedErMeasured.md`, `docs/measure_pfe_proxy.py`, prior reviews `docs/reviews/2026-10-22-{pfe,signed-er}-review.md`, wiring diffs in `README.md`, `docs/IndicatorDictionary.md`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `pandas_ta/momentum/__init__.py`, `tests/test_altport2_ports.py`
**Type:** code + text
**Verdict:** REVISE

## Findings

### CRITICAL
- **Done-when; docs/PfeMeasured.md status line and Gate C/E/F rows** — Neither exit condition of the task is met. `../Backtesting` is not on this machine, and no `measure_*_overlap_full.py` exists under /home/blue. That leaves three gaps: Gate C has no real-data counts, Gate E has never been run, and the parent-repo half of Gate F has never been run. `pfe` sits uncommitted in `Category`, neither shipped nor reverted. The doc does honestly say "OWED / verdict pending".
  - Fix: either (a) bring the parent repo onto this machine, then run `measure_pfe_overlap_full.py` and both suites, or (b) get the owner's approval to revert on the proxy evidence (ρ 0.874 vs summed `CMO_10`, 0.900 at σ 5%), delete the five touch points, and relabel the doc "REVERTED on proxy; Gate E not run".

### MAJOR
- **docs/MLCompanionContract.md:22** — The patched dictionary now has 213 `SF` columns, but the contract still quotes 212 SF / 565 tagged. As a result, `test_ml_companions::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts` fails with `[('SF', 212, 213)]`.
  - Fix: change it to 213 / 566 and add the note "(212 -> 213 on pfe: `PFE_10_5`)". Undo that edit on a revert.
- **docs/PfeMeasured.md:69 (Gate F row)** — The row claims "42 failed / 3,087 passed … same failures". The measured result is 43 failed / 3,086 passed / 85 skipped / 1 error, and the extra failure is the one this port caused.
  - Fix: fix the contract first, re-run the suite, then copy in the real counts and separate the environment-only failures from the new ones.
- **docs/PfeMeasured.md:19-26; pfe.py docstring; tests/test_pfe.py:7-9** — The doc says Hannula used raw-price legs and is therefore not scale-free, but cites no source. The common MetaStock form uses percent ROC, which is already scale-free. That last point is the reviewer's recall and has not been verified.
  - Fix: cite the page, or mark the claim "unverified". Then measure the ρ of the percent-ROC Hannula form against `PFE_10_5`.

### MINOR / NIT
- **MINOR tests/test_pfe.py:211-213** — The `0 < fires < n` check can never fail, because the warm-up NaNs already guarantee `< n`, so a constant ±100 column would still pass.
  - Fix: assert `nunique() > 100` and that both signs appear, and pin the 612 / 578 counts.
- **MINOR tests/test_wiring_accessors.py + test_altport2_ports.py** — When the two files run in the same session, `Category` gets mutated, so the count test sees 231 instead of 234. This is pre-existing test pollution, not something pfe introduced.
  - Fix: deep-copy or restore `Category` in a fixture, and track it as a separate issue.
- **NIT tests/test_pfe.py** — `offset` and `fillna` are still not tested. This was already raised in the prior review.
  - Fix: add the shift test and the no-NaN-after-fillna test.
- **NIT docs/IndicatorDictionary.md:29-31** — The text says "all call cleanly on pandas 2.3.3", but one row comes from a probe run on pandas 3.0.6.
  - Fix: regenerate on 2.x, or reword the sentence.

## What checks out (verified by the reviewer)
- `pfe.py` agrees with an independent loop to within 1e-9.
- Gate B is a real importlib + exec mutant test. Both mutants are caught on 31 of 31 checks, and the real module shows 0 leaks.
- Gate D: the ×8 and ×64 runs are bit-identical. The ×10 and ×3.7 runs differ by at most 2.7e-13.
- All five touch points are wired. README reads 234/242, and `test_readme_counts` passes.
- No `signed_er` leftovers remain in code or tests.
- Every proxy number in both Measured docs reproduces exactly via `docs/measure_pfe_proxy.py`.

## Resolution (2026-10-22)

Fixed the same day; the follow-up review is `2026-10-22-pfe-fix-1-3-review.md` (PASS):
- **MAJOR, MLCompanionContract.md:22** — fixed: 566 tagged / 213 `SF`; `test_ml_companions` passes.
- **MAJOR, PfeMeasured.md Gate F row** — fixed: the suite now measures 42 failed / 3,087 passed / 85 skipped / 1 error. The "43" above was correct when it was written. The pre-port baseline is labelled inferred, because it was not re-measured.
- **MINOR, test_pfe.py vacuous fires check** — fixed: the test now asserts > 100 distinct values and pins 612 positive / 578 negative.

Still open: the CRITICAL (real-data Gate C, Gate E and the parent-repo suite, all blocked on the absent parent repo), the unsourced Hannula raw-price MAJOR, the `Category` test-pollution MINOR, and both NITs.

## Summary

The task is not complete. The engineering is sound: the formula, the causality mutants and the scale invariance all hold, and every proxy number reproduces. But the task closes only on a full Gates A–F ship or a measured revert, and neither has happened. Gate E and the parent-repo suite cannot run because the parent repo is absent. The port also introduced a new test failure (the ML contract's SF count), which makes the doc's Gate F line false. The stated reason for departing from Hannula is unsourced and may be wrong. The proxy evidence and the pre-registered expectation both point to a revert. The fastest honest close is an owner-approved revert, with PfeMeasured.md kept as the receipt and labelled "Gate E not run".
