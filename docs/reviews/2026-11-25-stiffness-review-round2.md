# Brutally Honest Review — stiffness (issue #259), round 2

**Date:** 2026-11-25
**Target:** docs/StiffnessMeasured.md, pandas_ta/trend/stiffness.py, docs/reviews/2026-11-24-stiffness-review.md (files changed since round 1), plus a check of whether round 1's MAJOR finding is resolved
**Type:** code (plus a text receipt)
**Verdict:** PASS

## Findings

### MINOR / NIT
- **NIT — docs/StiffnessMeasured.md §Z** — The receipt says "~1.7 ms per call". I reran `python docs/measure_stiffness.py` on 2026-11-25 and it printed `stiffness 1.237 ms per call on 1500 bars`. That is about 27% below the quoted figure, so even the rounded "~1.7 ms" does not match a fresh run. The "this machine, this run" label means this is not a false claim. It is still a point timing that the script will not reproduce, in a receipt whose header says the script prints every number.
  - Fix: Give the timing as a range, e.g. "1–2 ms per call on 1,500 bars (varies run to run; §Z of the script prints this run's figure)". Alternatively, add §Z to the receipt's exception list as a number that is not reproducible.
- **NIT — pandas_ta/trend/stiffness.py docstring, "a steadily rising frame, and the `trend` frame (drift 0.003/bar), read exactly 100 on every one (§C1, §C2)"** — The §C2 citation is wrong for this sentence. Receipt §C2 covers only the `flat` frame, where the close sits on its band. The claim that `rising` and `trend` read 100 is backed by §C1 alone. Every other §-reference in the module points at the right section, including the comment fixed from §A4 to §A3 (ddof=1 is in §A3; truncation is in §A4).
  - Fix: Move "§C2" next to the flat-frame clause, e.g. "A flat frame reads exactly 0 on every fired bar (... strict; §C2); a steadily rising frame, and the `trend` frame (drift 0.003/bar), read exactly 100 on every one (§C1)."

## Summary

The round-1 MAJOR is fixed. Grepping StiffnessMeasured.md, stiffness.py, measure_stiffness.py and test_stiffness.py finds no "0.7718", "16 frames" or "screening", so the §L sentence is gone. I reran the script and compared §L (0.8099 / +0.3375 / +0.8447, Z_30 0.1180, PSL_12 0.0415, zscore(100) 0.5401, 60-bar mean 0.9525) and §C1, §D1, §D2, §D3 and §G1 with its output. All match. I did not re-check §A1–§B2 this round because their numbers were not in the diff. The round-1 MINOR is also fixed. §F now quotes a targeted run, and I reran that exact seven-file command: `1690 passed, 8 skipped`, with exactly one skip reading `Gate E owed ... ['stiffness']`. Exception 1 now matches what §F contains, and the module comment now points at §A3 as it should. Leaving the `**kwargs` swallowing in place was a choice made on a MINOR, so it does not block this round. The round-1 review file is a historical record and adds no new claims. Nothing critical or major remains, only two citation and timing nits.

I did not run the full suite or Backtesting's suite. I also did not re-review the files that were unchanged since round 1.
