# Brutally Honest Review — maxvol_adv

**Date:** 2026-10-28
**Target:** uncommitted change on `B2-MAXVOL14-ADV50`: `pandas_ta/volume/maxvol_adv.py`, `tests/test_maxvol_adv.py`, `docs/MaxvolAdvMeasured.md`, `docs/EquivalentStrategies.md`, wiring in `pandas_ta/volume/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, count edits in `tests/test_altport2_ports.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`
**Type:** code
**Verdict:** REVISE

## Findings

### CRITICAL
- **docs/MLCompanionContract.md:27** — This change edited the sentence, and two of its counts are still wrong. Counted with the guard's own regex, the dictionary has 570 tagged columns (SF 216, PX 137, BIN 103, ORD 50, CONST 41, ?? 21, PX2 2). The text says 568 columns and 49 `ORD`, and its own seven numbers add up to 569. `ORD` has been stale since `range_compress_run`'s `RCR_100` went in. The guard (`test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`) checks only PX/SF/BIN/PX2, so it misses this.
  - Fix: change the text to "570 tagged columns" and "50 `ORD`". Extend the guard to ORD, CONST and `??`, and assert that the quoted total equals the sum of the tags.

### MAJOR
- **docs/MaxvolAdvMeasured.md, Gates C/E/F** — The issue's done condition (A–F shipped, or measured and reverted) is not met. Gate C has no real data, Gate E only repeats the prototype's figure, and Gate F is not met. Even so, the column is in `Category` and the counts were bumped.
  - Fix: run Gates C/E/F on the machine that has `../Backtesting` and record the numbers. Until then, keep the branch unmerged and the issue open with the status "C/E/F owed".
- **docs/MaxvolAdvMeasured.md, "Gate F, this repo"** — There is no clean-baseline column. The pandas-3 "42 match the receipt above" compares against a receipt taken on a different base (479cd8f), and only 1 of the 42 failures was spot-checked.
  - Fix: run both venvs on the current base with the change stashed, diff the lists of failing test node IDs, and add a "clean `<sha>`" column. Say "identical" only if the diff is empty.

### MINOR / NIT
- **tests/test_maxvol_adv.py:15 vs MaxvolAdvMeasured.md Gate D** (MINOR) — The ×10/×3.7 tolerances disagree: the test says 4.5e-16, the doc says 2.2e-16 / 4.4e-16, and the reviewer measured 2.217e-16 / 3.925e-16.
  - Fix: quote the measured figures, the same way in both places.
- **maxvol_adv.py docstring, "the ratio cancels a volume rescaling"** (MINOR) — The claim is unqualified. It is exact only for power-of-two factors.
  - Fix: add "bit-identical for ×8/×64; within ~4e-16 relative otherwise".
- **maxvol_adv.py "Source" paragraph; Gate A row** (MINOR) — The post fixes neither the windows (14/50) nor the ADV. Both are the prototype's choices, known only from the issue text.
  - Fix: say so plainly in both places.
- **test_zero_adv_is_nan_not_inf, short > long case** (MINOR) — The case returns all NaN, so the not-inf assert would also pass for a function that returns nothing but NaN. Nothing covers negative ADV, although the docstring promises "NaN where ADV <= 0".
  - Fix: assert an exact finite value for short > long. Add a negative-ADV case.
- **MaxvolAdvMeasured.md, "Is it already shipped? No."** (MINOR) — The check covered pandas_ta only. The engine's 687-column comparator pool was not inspected.
  - Fix: scope the "No" to pandas_ta, and say Gate E on the port is what settles the question.
- **maxvol_adv.py, min_periods = window** (MINOR) — One NaN volume bar blanks the next 50 output bars. This is not documented.
  - Fix: add one docstring line. Report the NaN count on BIST when Gate C runs.
- **IndicatorDictionary.md, hand-patched row** (NIT) — The generator output the row came from was thrown away.
  - Fix: keep the row's provenance in the commit message or in the Measured doc.
- **docs/EquivalentStrategies.md** (NIT) — This file belongs to an earlier task and is sitting in this change.
  - Fix: commit it separately with `docs` scope.

## Summary

The math is right and the tests are good. The independent loop agrees, both look-ahead mutants are caught at 31/31 and the real module at 0/31, the ×1000 future fixes the max-hiding hole, and the synthetic counts reproduce exactly. All five wiring touch points are present. The paperwork is where it fails. The contract sentence this change edited quotes 568 columns and 49 ORD against a dictionary with 570 and 50: exactly the "count written without a run" defect CLAUDE.md names, and the guard is too narrow to catch it. The done condition is not met (C/E/F open), but the column ships in `Category`. Gate F has no clean-baseline diff. The tolerance figures disagree across files. Gate A's definition is second-hand, and the docstring does not say so.

Not checked by the reviewer: pytest itself or the full suite (the sandbox is read-only; the tests were run by direct call), pandas 3, the Reddit post, the prototype, anything in Backtesting.
