# Brutally Honest Review — tao (issue #266, TAO-10-5)

**Date:** 2026-11-18
**Target:** README.md, docs/IndicatorDictionary.md, docs/MLCompanionContract.md, pandas_ta/__init__.py, pandas_ta/core.py, pandas_ta/momentum/__init__.py, tests/test_altport2_ports.py, docs/TaoMeasured.md, docs/measure_tao.py, pandas_ta/momentum/tao.py, tests/test_tao.py
**Type:** code (dominant), with text/analysis receipts
**Verdict:** REVISE

## Findings

### CRITICAL
- **pandas_ta/momentum/tao.py, `tao.__doc__` paragraph "NaN on bars 0 .. 13 (`length + ma_length - 2`)"** — This is off by one. Bar 13 is the first bar with a value, not a NaN bar. §C prints `first 13` on all seven moving frames. `test_the_warm_up_is_a_constant_13_bars` asserts `col.iloc[13:].notna().all()`, and a direct probe gave iloc[12..14] = [nan, 31.82, 26.74]. The shipped docstring therefore makes a false claim that contradicts the module's own receipt and tests.
  - Fix: Change it to "NaN on bars 0 .. 12 (the first `length + ma_length - 2` = 13 bars); the first value is on bar 13".

### MINOR / NIT
- **MINOR — tests/test_tao.py:27-28 (docstring item 2)** — "1 .. 21 bars below 0 or above 100 per 1,500-bar frame" is false for `coarse`, a firing frame where §C prints 0 bars below 0 and 0 above 100. It also merges two separate counts into one range.
  - Fix: Rewrite as "on six of the seven moving frames (`coarse` stays inside): 3 .. 18 bars below 0 and 1 .. 21 above 100 per 1,500-bar frame", which is what §C prints.
- **MINOR — docs/TaoMeasured.md §Gate D, "`flat` is bit-identical under the exact factors too, as all-NaN"** — `section_D` loops over `FIRING` only, so `measure_tao.py` never prints this. It only runs in the 400-bar test. That breaks the receipt's own rule that every number below is printed by the script.
  - Fix: In `section_D`, loop the exact factors over `NAMES` (including `flat`), or delete the sentence.
- **MINOR — docs/TaoMeasured.md §W, "A non-default midpoint is appended (`TAO_14_3_40`)"** — `section_W` never prints this name. It comes from `test_the_accessor_forwards_every_parameter`, not from the script.
  - Fix: Add `print(f"non-default    : {_run(df, length=14, ma_length=3, midpoint=40).name}")` and a `df.ta.tao(...)` bit-equality line to `section_W`.
- **MINOR — pandas_ta/momentum/tao.py, `_mid = "" if midpoint == 50.0 else f"_{midpoint:g}"`** — `:g` keeps only 6 significant digits, so different parameters produce the same column name. Probed: midpoint=40.0000001 gives `TAO_10_5_40`, the same name as midpoint=40. midpoint=1e6 gives `TAO_10_5_1e+06`. Column names are API in this repo. midpoint=0 is handled correctly (`is not None`, giving `TAO_10_5_0`) and midpoint=50.5 gives `TAO_10_5_50.5`, so neither is a problem.
  - Fix: Use a lossless format, e.g. `f"_{int(midpoint)}" if midpoint.is_integer() else f"_{midpoint!r}"`. Add a test asserting that 40 and 40.0000001 get different names and that 50.5 gives `TAO_10_5_50.5`.
- **MINOR — tests/test_tao.py:47-50 (docstring item 5); docs/measure_tao.py:375** — "blanks nothing for L <= 9" and the general formula "`L - 9 + 4` bars from L = 10 on" were derived by hand. §C2 runs only L = 5, 9, 10, 11, 15. The script header also prints "each NaN O empties 5 TAO bars", which its own row contradicts (6 NaN O empty 10 bars, not 30).
  - Fix: Sweep L = 1 .. 20 in `section_C2` and print every row, or reword both claims as "at the five L measured". Change the printed header to "a run of k consecutive NaN O empties k + 4 TAO bars".
- **MINOR — docs/measure_tao.py:111-112 (`_coarse` docstring); docs/TaoMeasured.md "The frames"** — Two claims about the frames are wrong or never measured. The `_coarse` docstring says "flat 10-bar windows ... happen by rounding", but §C prints `flatHL 0` for `coarse`. "so a close sits on the window's extreme by rounding" and "the close is often exactly the bar's extreme" are never measured.
  - Fix: Delete "flat 10-bar windows" from the docstring. Either add a §C column counting bars with O in {0, 100} per frame, or drop the "sits on the extreme" and "often exactly the extreme" wording.
- **MINOR — pandas_ta/momentum/tao.py `mao = osc.rolling(ma_length).mean()`; tests/test_tao.py `_oracle`** — The issue says "NaN until 5 values of O exist". That matches the 13-bar warm-up, but it does not say what happens when an O inside the window is NaN. The port reads it strictly: any NaN O blanks the next 5 bars. The oracle copies the same rule, so Gate A cannot tell this reading from the other choice (`min_periods`, or a mean that skips NaN). Neither the receipt nor the docstring says this was the porter's reading.
  - Fix: Add a sentence under receipt §A1 and in the docstring: "'NaN until 5 values of O exist' is read as a full window of 5 non-NaN O; an interior NaN O blanks 5 bars (§C2). This is the porter's reading, and the owner may choose `min_periods` instead."
- **NIT — docs/TaoMeasured.md §Gate F, "1,333 passed, 8 skipped"** — `measure_tao.py` does not print this count, and it depends on test order. Running `tests/test_wiring_accessors.py` before `tests/test_altport2_ports.py` fails `test_the_category_count_moved_by_exactly_three` ("Category total 355, expected 358"). Some earlier test mutates `Category` in place. That is very likely not caused by this port, but the reviewer did not compare against a clean baseline. Alone, `test_altport2_ports` passes.
  - Fix: Quote the exact pytest command and file order that produced 1,333, and open a separate issue for the in-place `Category` mutation.

## Summary

The maths and wiring hold up. Gate A matches the issue line by line (10-bar window includes the current bar, NaN on a zero range, plain 5-bar rolling mean, `midpoint` subtracted correctly), and all five touch points are present. The accessor forwards `length`/`ma_length`/`midpoint`/`offset` under the right names, and helpers come from `pandas_ta.utils`. README (358/366, momentum 88), `CATEGORY_TOTAL` 358 and the dictionary census (703/341) match what the package prints. Gate B is a real exec'd mutant test with five live mutants, and Gate D's numbers match the script. The reviewer cross-checked the receipt against §A1/A2/A3/B/B1/C/C2/D/F/W/W2/Z and almost every number reproduces. `tests/test_tao.py` passes: 142 tests. The port still fails review because the shipped docstring states the warm-up wrong ("NaN on bars 0 .. 13" when bar 13 fires). That is the "claim written before it was measured" defect CLAUDE.md warns about, sitting next to a receipt that measured the right answer. The rest is smaller. A few receipt sentences are never printed by the script. Some general claims were derived by hand from five points. The `coarse` frame's description contradicts its own flat-window count. `:g` naming can give two different midpoints the same column name. The "5 values of O" reading is never stated as a choice. Fix the docstring line and these items, rerun, and it passes.

Not checked by the reviewer: Gate F's six-file run behind 1,333, and the full suite. The `Category` count failure that depends on test order is very likely older than this port but is unconfirmed.
