# Brutally Honest Review — expand3_3pct port (issue #201), round 2

**Date:** 2026-11-25
**Target:** docs/Expand33PctMeasured.md, docs/measure_expand3_3pct.py, docs/reviews/2026-11-25-expand3-3pct-review.md (re-review: round-1 MAJOR resolution + files changed since round 1)
**Type:** code (with text receipt)
**Verdict:** PASS

## Round-1 MAJOR — resolved

- **docs/Expand33PctMeasured.md:57 (unmeasured `ROC_2` ρ 0.389)** — RESOLVED. The new §E0 in `docs/measure_expand3_3pct.py` runs in about 2.4 s and prints exactly what the receipt quotes:
  - `ROC_2` median 0.3885 over 8 frames, range [0.2971, 0.5193]
  - `INC_2` 0.2559 [0.1814, 0.3558]
  - `HIGHER_HIGH-LOWER_LOW` 0.1822 [0.1376, 0.2333]
  - fires per frame [0, 49, 169, 0, 57, 196, 0, 69, 160, 0, 62, 188]: the zeros are seeds 0/3/6/9, which are exactly the 1%-vol frames
  - exact high ties 6..118

  The section list includes E0, and no "0.389" or "analysis before porting" text remains outside docs/reviews.

## Findings

### MINOR / NIT
- **MINOR — docs/Expand33PctMeasured.md:57 (Gate E row, §E0 sentence)** — The E0 screen gives a per-frame median ρ of 0.3885 against `ROC_2`. That is higher than the prototype's whole Gate E maximum (0.2935 vs `Dist_to_FWMA_pct`), and the receipt says nothing about it. A reader could take the two figures as consistent, or as contradictory. They are different measurements: synthetic per-frame medians on one side, pooled real-data ρ on the other. Nowhere does the receipt say they cannot be compared, or that Gate E on the port must include short-horizon return columns such as `ROC_2`.
  - Fix: Add one clause after the E0 figures: "synthetic per-frame medians, not comparable to the pooled real-data Gate E ρ above; the owed Gate E run must include `ROC_2`/`INC_2` among its comparators."
- **MINOR — docs/measure_expand3_3pct.py:422-431 (E0 comparator set)** — The printout calls these "the nearest shipped columns", but nothing was measured to choose them. All three are close- or structure-based. The signal is built only from 2-bar high and low steps, so 2-bar ROC of `high` and `low`, or the existing high/low helpers, would be closer. The labels are honest and the numbers are not cherry-picked downward, because `ROC_2` is the strongest of the three. Still, "nearest" is a claim with no run behind it.
  - Fix: Change the printout to "three hand-picked shipped columns". Or add `ta.roc(d["high"],2) - ta.roc(d["low"],2)`, or similar high/low-based comparators, to `comps` and quote whichever is largest.
- **NIT — docs/measure_expand3_3pct.py:429-430** — `bos` columns are picked by position (`iloc[:, 2]` / `iloc[:, 3]`). It is correct today: the output columns are `['BOS_BULL','BOS_BEAR','HIGHER_HIGH','LOWER_LOW']`, which the reviewer checked. But the script silently measures the wrong thing if `bos` ever reorders its output.
  - Fix: Use `b["HIGHER_HIGH"] - b["LOWER_LOW"]`.
- **NIT — docs/measure_expand3_3pct.py:470** — Adding `"E0": section_E0` made the `SECTIONS` dict line longer than the other lines in the file.
  - Fix: Re-wrap it to match the surrounding lines.
- **MINOR (still open from round 1, non-blocking) — pandas_ta/trend/expand3_3pct.py:8,17; :71-74; tests/test_expand3_3pct.py (h1/l1-lead mutants); docs/IndicatorDictionary.md CONST row; receipt §Z timings; trend/__init__.py:17 and core.py:2583 ordering; expand3_3pct.py:62 "2.913%"** — None of round 1's MINOR/NIT items were addressed.
  - Fix: Apply the fixes listed in docs/reviews/2026-11-25-expand3-3pct-review.md.

## Summary

Round 1's only MAJOR is fixed. The unmeasured "analysis before porting … ROC_2 0.389" sentence is gone, and a real §E0 section now produces every figure that replaced it, matching the receipt exactly. Using `import pandas_ta as ta` inside a measurement function follows established precedent (measure_ffd_proxy, measure_kalman_trend_proxy, measure_trend_scan_proxy and others), and the indicator itself is imported from its own module. The round-1 report faithfully records round 1. What is left is small: "nearest shipped columns" is asserted rather than measured, the receipt does not say the E0 ρ cannot be compared with the higher prototype Gate E ρ, and round 1's non-blocking nits are all still open.

Reviewer's stated limits: B1, the full suites and the other sections were not run; the dictionary was not regenerated; the round-1 report was checked against the brief, not against round 1's own transcript.
