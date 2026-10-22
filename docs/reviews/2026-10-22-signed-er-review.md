# Brutally Honest Review — signed_er port

**Date:** 2026-10-22
**Target:** `pandas_ta/momentum/signed_er.py`, `tests/test_signed_er.py`, `docs/SignedErMeasured.md`, wiring in `pandas_ta/momentum/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, count bumps in `README.md`, `tests/test_altport2_ports.py`
**Type:** code (plus text for the Measured doc)
**Verdict:** REVISE

## Findings

### MAJOR
- **docs/SignedErMeasured.md:9 vs :43** — The status line says "Gates A–D cleared", but the doc's own Gate C row says synthetic only, real-data counts owed. CLAUDE.md defines Gate C as firing on real data, so this overclaims.
  - Fix: change it to "Gates A, B, D cleared; Gate C synthetic only (real-data counts owed); Gate E OWED; verdict pending."
- **pandas_ta/momentum/signed_er.py:51; docs/SignedErMeasured.md:20** — PFE is attributed to "Hosking". PFE is Hans Hannula's (TASC, 1994), the very indicator the task names.
  - Fix: replace "Hosking's" with "Hannula's" in both places. In the doc, add one line saying the task's Hannula PFE was replaced by a signed Kaufman ER on the owner's instruction.
- **pandas_ta/momentum/signed_er.py:49-50; docs/SignedErMeasured.md:3-5** — "signed path efficiency" is quoted as a term Kaufman describes, with no page citation in the repo. Kaufman ch.17 gives the unsigned ER.
  - Fix: reword to "Signed variant of Kaufman's Efficiency Ratio (Kaufman 2013, ch.17); the signed path-efficiency idea is Hannula's PFE (ch.20), not shipped because it is not scale-free." Drop the quotation marks unless a page can be cited.
- **docs/IndicatorDictionary.md:37-38; README.md:9-11** — The dictionary was not regenerated. It still shows 233 / 241 and has no `signed_er` row, so the README's statement that all indicators are in the dictionary is now false. `docs/indicators/signed_er.md` is also missing.
  - Fix: run `python docs/gen_indicator_dictionary.py` and `python docs/gen_indicator_pages.py`, check for 234 / 242 and a `SER_10_5` row, and commit both.
- **signed_er.py:55; SignedErMeasured.md:30,41; tests/test_signed_er.py:6-8,28** — The "exact" identities with `er * sign` and `cmo(talib=False)/100` break on flat windows: SER gives 0 there, while er and cmo give NaN. The tests can't see this, because `_walk()` has no flat windows and `.max()` skips NaN.
  - Fix: qualify every statement as "on bars where path > 0". In the identity tests, use a `tick=0.05` walk, compare NaN masks, and assert SER is 0 wherever the reference is NaN.

### MINOR / NIT
- **MINOR tests/test_signed_er.py:30-31** — The "NaN hole the EMA carries forward" wording is wrong. `ewm(adjust=False)` holds its last value through a mid-series NaN; a NaN only survives if the series opens flat.
  - Fix: reword accordingly. Optionally add a mid-series flat case.
- **MINOR signed_er.py:33-34** — `fillna(method=...)` raises on pandas 3. This branch was copied from er.py and is untested.
  - Fix: use `.ffill()` / `.bfill()`, or drop the `fill_method` kwarg.
- **MINOR SignedErMeasured.md:32-34,43,50-61** — The proxy numbers (2.2e-16, 0.66 / 0.874, the Gate C counts, the ρ table) have no committed script or pinning test.
  - Fix: commit `docs/measure_signed_er_proxy.py` with fixed seeds, or pin the counts in the tests.
- **MINOR pandas_ta/__init__.py:56** — `signed_er` is in `Category` before Gate E, so a strategy sweep in the parent repo picks it up early.
  - Fix: add "Do not merge before Gate E" under "To close", or keep the indicator out of `Category` until Gate E runs.
- **NIT signed_er.py:78** — "in [-1, 1]" fails when drift > length (inherited from er).
  - Fix: document "for drift <= length", or clamp drift.
- **NIT SignedErMeasured.md:61-65** — The pre-registered guess (high ρ vs er) was falsified (ρ −0.0089), and the doc doesn't say so.
  - Fix: add one sentence saying so.
- **NIT pandas_ta/momentum/__init__.py:16** — The export breaks alphabetical order.
  - Fix: move it between `.rvgi` and `.slope`.

## Summary

The maths is fine and the mutant and scale tests are real. The summed-CMO identity is an honest finding that points straight to a revert. What fails is the text around the code. The status line overclaims Gate C. PFE is credited to the wrong author, and the Kaufman quote has no citation behind it. Two identities are stated as "exact" while the code's own flat-window special case breaks them. The dictionary wasn't regenerated, which makes the README edit false. Fix the attribution and the overclaims, qualify the identities, and regenerate the docs. It is then an acceptable pending-Gate-E receipt.

Reviewer note: the reviewer could not run anything. The Hannula attribution comes from its own knowledge of the literature.
