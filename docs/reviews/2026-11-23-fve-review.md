# Brutally Honest Review — fve port (issue #260)

**Date:** 2026-11-23
**Target:** README.md, docs/IndicatorDictionary.md, docs/MLCompanionContract.md, pandas_ta/__init__.py, pandas_ta/core.py, pandas_ta/volume/__init__.py, tests/test_altport2_ports.py, docs/FveMeasured.md, docs/measure_fve.py, pandas_ta/volume/fve.py, tests/test_fve.py
**Type:** code (with text receipts)
**Verdict:** REVISE

## Findings

### MAJOR
- **docs/FveMeasured.md, "Non-redundancy (synthetic, not Gate E)", the paragraph that begins "The analysis step's wider screen ran 12 synthetic tick-rounded frames (800 bars)..."** — The acceptance criteria say every number in the receipt must be reproducible by docs/measure_fve.py. This paragraph quotes 12 frames, 800 bars, 534 columns, 0.8204 for `G191_040_26`, 0.7429 for `KVOs_34_55_13` and 0.6857 for `VZO_14`. None of them comes from the script, and the receipt itself says they came from "a throw-away script outside the repo". Disclosing the gap does not meet the rule: this is the "claim with no matching run" pattern that CLAUDE.md names as the main historical defect. The paragraph's 0.6857 for `VZO_14` also sits next to the script's own 0.6762 for `VZO_14`, so a reader sees two numbers for one comparison.
  - Fix: Delete the paragraph. The script's 1-frame and 12-frame Spearman blocks already support the "Gate E risk" note. Alternatively, move the wider screen into docs/measure_fve.py: loop over `ta.Category`, then print how many default columns compute and the top 3 per-frame median |rho|. Quote only what that prints.

### MINOR / NIT
- **MINOR — pandas_ta/volume/fve.py:57** (`cutoff = float(cutoff) if cutoff and cutoff > 0 else 0.003`) — Passing `cutoff=0`, the natural no-dead-zone variant, silently gives 0.003, and the column is named `FVE_22`. A caller who asks for the no-band form gets the default under the default name, with no warning. Negative values are also swallowed silently.
  - Fix: Use `cutoff = float(cutoff) if cutoff is not None and cutoff >= 0 else 0.003`, so that `cutoff=0` yields `FVE_22_0.0`. Add one test showing `fve(*_frame(200), cutoff=0).name == "FVE_22_0.0"` and that its output differs from the default. Alternatively, state in the Args block that `cutoff <= 0` falls back to 0.003.
- **NIT — tests/test_altport2_ports.py, the `CATEGORY_TOTAL = 380` comment** — The new entry reads `(volume),+1 on issue #146's ...`: there is no space after the comma, unlike every other entry. It also doesn't point to the receipt or say that Gate E is pending, as neighbouring entries do.
  - Fix: Write `+1 on issue #260's fve port (volume; Gate E pending, run by issue-solver after this session; see docs/FveMeasured.md), +1 on issue #146's ...`.
- **NIT — pandas_ta/volume/fve.py, the function docstring's "Bounded in [-100, 100]" and the Returns line's "in [-100, 100]"** — The bound only holds when volume is non-negative. The code does not check this, and the docstring doesn't state the assumption.
  - Fix: Write "in [-100, 100] for non-negative volume".

## Summary

The port itself is correct, and the reviewer checked each point below by running the code:

- **Gate A:** the formula matches the issue line by line. The band is strict, bar 0 is NaN, the first value is at bar 22, the rolling sum stands in for SMA×22, and an all-zero volume window gives NaN.
- **Wiring:** all five touch points are present. The accessor passes `length`, `cutoff` and `offset` under their own names.
- **Gate B:** the mutant is real (source read via importlib, exec'd in memory). The real module leaks at 0 of 35 offsets; the mutant leaks at 35 of 35.
- **Gate D:** output is bit-identical at all four scale factors.
- **Receipt and test numbers:** every number the script prints matches the receipt. The test docstring's 900-bar figures, re-run, also match: 878 values, 435 positive / 443 negative, and a difference of 0 at ×10 and ×3.7.
- **Counts:** `Category` has 380 entries, 44 of them in `volume`. `tests/test_readme_counts.py` pins the README's 388 accessor count and passes.
- **Tests:** tests/test_fve.py has 24 tests and all pass.
- **Dictionary:** regenerating docs/IndicatorDictionary.md gives a byte-identical file.

One thing blocks a PASS: the receipt quotes a wider screen from a script that is not in the repo. Delete that paragraph or move the screen into docs/measure_fve.py, and the port passes.

The reviewer did not run the full suite or the parent repo. Gate E is owed and out of scope.

Housekeeping: during the review, `python docs/gen_indicator_dictionary.py --help` wrote a stray copy of the dictionary to `./--help`, because the script reads its first argument as the output path. The main session deleted it, and the working tree now holds only the port's files.
